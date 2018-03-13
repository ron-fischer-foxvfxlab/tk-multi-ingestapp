
def usage():

    print "USAGE:"
    print "------"
    print "To extract timecode from movie.mov, do as follows:"
    print ""
    print " $ python ccr2_extract_timecode2.py movie.mov"
    print " 23:59:58:57 60"

import sys

def framesToTimecode(nframes, fps):
    '''
    Converts frames since midnight to timecode [HH,MM,SS,FF].
    Assumes non-drop.
    '''
    f = nframes
    
    k = 60*60*fps
    hours = f/k
    f = f - hours*k
    
    k = 60 * fps
    minutes = f/k
    f = f - minutes*k
    
    k = fps
    seconds = f/k
    frames = f - seconds*k
    
    return [hours,minutes,seconds,frames]

def u_from_be(numbytes,be):
    ret = 0
    for i in range(numbytes):
        ret = ret + (be[i] << ((numbytes-i-1) * 8))
    return ret

def read_u(numbytes,f):
    return u_from_be(numbytes,[ord(c) for c in f.read(numbytes)])
    
def read_atom_children(f,parent):

    while(True):
    
        atom = {'parent':parent,'children':[],'data':''}
    
        atom['offset'] = f.tell()
        
        if atom['offset'] == parent['offset'] + parent['size']:
            break
        
        atom['size']   = read_u(4,f)
        atom['type']   = f.read(4)
        
        headersize = 8
        
        if atom['size'] == 1:
            atom['size'] = read_u(8,f)
            headersize = headersize + 8
            
        #print 'Type:',atom['type']

        parenttypes = ['moov','trak','mdia','minf','stbl']
        datatypes   = ['tmcd']
        
        if atom['type'] in parenttypes:
            read_atom_children(f,atom)
        elif atom['type'] in datatypes:
            atom['data'] = f.read(atom['size']-headersize)
        elif atom['type'] == 'mdat':
            atom['data'] = f.read(4)
        elif atom['type'] == 'stsd':
            f.read(8)
            read_atom_children(f,atom)
            
        parent['children'].append(atom)
        
        f.seek(atom['offset'] + atom['size'])

def print_hierarchy(atom,level):
    print level*'   ' + atom['type']
    for child in atom['children']:
        print_hierarchy(child,level+1)
        
def extract_atoms(f):
    f.seek(0,2)
    filesize = f.tell()
    f.seek(0)
    
    root = {'offset':0,'size':filesize,'type':'root','children':[]}
    read_atom_children(f,root)
    
    return root

def find_atom(atomtype,root):
    for child in root['children']:
        if child['type'] == atomtype:
            return child
        else:
            a = find_atom(atomtype,child)
            if a is not None:
                return a
    return None

def extract_fps(root):
    a = find_atom('tmcd',root)
    return ord(a['data'][24])
    
def extract_framessincemidnight(root):
    a = find_atom('mdat',root)
    return u_from_be(4,[ord(c) for c in a['data'][:4]])

if __name__ == "__main__":

    if len(sys.argv) != 2:
        usage()
        exit(0)
        
    fpath = sys.argv[1]

    with open(fpath, 'rb') as f:
        root = extract_atoms(f)
    
    #print_hierarchy(root,0)

    framessm  = extract_framessincemidnight(root)
    fps       = extract_fps(root)
    
    tc = framesToTimecode(framessm,fps)

    print '%0.2d:%0.2d:%0.2d:%0.2d %d' % (tc[0],tc[1],tc[2],tc[3],fps)
