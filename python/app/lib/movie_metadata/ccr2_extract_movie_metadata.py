import sys, os, struct


def usage():
    print "USAGE:"
    print "------"
    print "To extract metadata from movie.mov, do as follows:"
    print ""
    print " $ python %s movie.mov" % (os.path.basename(__file__))


def timecodeToFrames(h32, m32, s32, f32, fps32, drop):
    frames = (h32 * 3600 + m32 * 60 + s32) * fps32 + f32

    if drop:
        droppedFrames = h32 * 108 + 2 * (m32 - m32 / 10)
        frames -= droppedFrames

    return frames


'''
Converts frames since midnight to timecode [HH,MM,SS,FF].
'''


def framesToTimecode(nframes, fps, drop):
    # if dropping counts, normalize to non-drop by adding frame counts what would have been dropped.
    if drop:
        f10m = 10 * 60 * fps - 18  # number of frames in 10 minutes of timecode that drops counts (9mins*2frames)
        ten_minutes = nframes / f10m  # number of 10 minutes
        frames_to_add = ten_minutes * 18  # add number of frames that would have been dropped in all 10 minute spans
        frames_left = nframes - ten_minutes * f10m  # frames left to normalize in a similar way

        if (frames_left >= 60 * fps):  # 60*fps is the number of frames in 1 minute
            frames_to_add += 2 * (
            1 + (frames_left - 60 * fps) / (60 * fps - 2))  # 2 frames for every minute after the first one

        nframes += frames_to_add

    f = nframes

    k = 60 * 60 * fps
    hours = f / k
    f = f - hours * k

    k = 60 * fps
    minutes = f / k
    f = f - minutes * k

    k = fps
    seconds = f / k
    frames = f - seconds * k

    return [hours, minutes, seconds, frames]


def u_from_be(numbytes, be):
    ret = 0
    for i in range(numbytes):
        ret = ret + (be[i] << ((numbytes - i - 1) * 8))
    return ret


def read_u(numbytes, f):
    return u_from_be(numbytes, [ord(c) for c in f.read(numbytes)])


def read_atom_children(f, parent):
    while (True):

        atom = {'parent': parent, 'children': [], 'data': ''}

        atom['offset'] = f.tell()

        if atom['offset'] == parent['offset'] + parent['size']:
            break

        atom['size'] = read_u(4, f)
        atom['type'] = f.read(4)

        headersize = 8

        if atom['size'] == 1:
            atom['size'] = read_u(8, f)
            headersize = headersize + 8

        if atom['size'] == 0:
            print "WARNING: Corrupt atom '%s' in parent '%s'. Skipped." % (atom['type'], parent['type'])
            f.seek(parent['offset'] + parent['size'])
            break

        parenttypes = ['moov', 'trak', 'mdia', 'minf', 'stbl', 'udta']
        datatypes = ['tmcd', 'co64', 'json']

        # get a little bit of the data, whatever that may be
        pos = f.tell()
        atom['data'] = f.read(min(1024, atom['size'] - headersize))
        f.seek(pos)

        if atom['type'] in parenttypes:
            read_atom_children(f, atom)
        elif atom['type'] in datatypes:
            atom['data'] = f.read(atom['size'] - headersize)
        elif atom['type'] == 'mdat':
            atom['data'] = f.read(4)
        elif atom['type'] == 'stsd':
            f.read(8)
            read_atom_children(f, atom)

        parent['children'].append(atom)

        f.seek(atom['offset'] + atom['size'])


def print_hierarchy(atom, level):
    print level * '   ' + atom['type']
    for child in atom['children']:
        print_hierarchy(child, level + 1)


def extract_atoms(f):
    f.seek(0, 2)
    filesize = f.tell()
    f.seek(0)

    root = {'offset': 0, 'size': filesize, 'type': 'root', 'children': []}
    read_atom_children(f, root)

    return root


def find_atom(atomtype, root):
    for child in root['children']:
        if child['type'] == atomtype:
            return child
        else:
            a = find_atom(atomtype, child)
            if a is not None:
                return a
    return None


def find_atoms(atomtype, root, list):
    for child in root['children']:
        if child['type'] == atomtype:
            list.append(child)
        else:
            find_atoms(atomtype, child, list)


def extract_fps(root):
    a = find_atom('tmcd', root)

    timescale = u_from_be(4, [ord(b) for b in a['data'][16:20]])
    frameDuration = u_from_be(4, [ord(b) for b in a['data'][20:24]])

    return float(timescale) / float(frameDuration)


def find_video_trak(root):
    vmhd = find_atom('vmhd', root)

    trak = vmhd

    while (trak['type'] != 'trak'):
        trak = trak['parent']

    return trak


def find_timecode_trak(root):
    tmcd = find_timecode_tmcd(root)

    trak = tmcd
    while (trak['type'] != 'trak'):
        trak = trak['parent']

    return trak


def extract_json(root):
    udta = find_atom('udta', root)
    json = find_atom('json', udta)
    return json['data']


def find_timecode_tmcd(root):
    tmcds = []
    find_atoms('tmcd', root, tmcds)

    for tmcd in tmcds:
        if tmcd['parent']['type'] == 'stsd':
            return tmcd

    return None


def extract_tcRate(root):
    a = find_timecode_tmcd(root)
    return ord(a['data'][24])


def find_timecode_drop(root):
    tmcd = find_timecode_tmcd(root)
    flags, = struct.unpack(">I", tmcd['data'][12:16])
    drop = (flags & 1 == 1)

    return drop


def find_timecode_fileoffsets(root):
    tmcd = find_timecode_tmcd(root)
    stsd = tmcd['parent']

    # find parent trak by going up the hierarchy
    trak = tmcd
    while (trak['type'] != 'trak'):
        trak = trak['parent']

    try:
        stco = find_atom('stco', trak)
        numEntries, = struct.unpack('>I', stco['data'][4:8])
        unpackstr = '>%dI' % (numEntries)
        chunkOffsets = struct.unpack(unpackstr, stco['data'][8:8 + numEntries * 4])
    except:
        co64 = find_atom('co64', trak)
        numEntries, = struct.unpack('>I', co64['data'][4:8])
        unpackstr = '>%dQ' % (numEntries)
        chunkOffsets = struct.unpack(unpackstr, co64['data'][8:8 + numEntries * 8])

    return chunkOffsets


def find_timecode_fileoffset(root):
    tmcd = find_timecode_tmcd(root)
    stsd = tmcd['parent']

    # find parent trak by going up the hierarchy
    trak = tmcd
    while (trak['type'] != 'trak'):
        trak = trak['parent']

    try:
        stco = find_atom('stco', trak)
        chunkOffset, = struct.unpack('>I', stco['data'][8:12])
    except:
        co64 = find_atom('co64', trak)
        chunkOffset, = struct.unpack('>I', co64['data'][8:16])

    return chunkOffset


def extract_numTcFrames(root):
    trak = find_timecode_trak(root)
    edts = find_atom('edts', trak)

    flags, numEntries, trackDuration, mediaTime, mediaRate = struct.unpack(">5I", edts['data'][8:28])
    mediaRate = (mediaRate >> 16) + (mediaRate & 0xFFFF) * 1e-16

    tmcd = find_timecode_tmcd(root)
    timescale, frameDuration, fps = struct.unpack(">2IB", tmcd['data'][16:25])

    return trackDuration / frameDuration


def test(root):
    # mvhd = find_atom('mvhd',root)
    # flags, creationTime, modificationTime, timescale, duration = struct.unpack(">5I", mvhd['data'][0:5*4])
    return

def extract_timing(fpath):
    f = open(fpath, 'rb')
    root = extract_atoms(f)
    try:
        tcRate = extract_tcRate(root)
        drop = find_timecode_drop(root)
        tcOffset = find_timecode_fileoffset(root)
        f.seek(tcOffset)
        framessm = read_u(4, f)
        tcIn = framesToTimecode(framessm, tcRate, drop)
        fps = extract_fps(root)
        tcFrames = extract_numTcFrames(root)
        tcOut = framesToTimecode(framessm + tcFrames - 1, tcRate, drop)
        tcInStr = '%0.2d:%0.2d:%0.2d:%0.2d' % (tcIn[0], tcIn[1], tcIn[2], tcIn[3])
        tcOutStr = '%0.2d:%0.2d:%0.2d:%0.2d' % (tcOut[0], tcOut[1], tcOut[2], tcOut[3])
        f.close()
        f = None
        return (tcInStr, tcOutStr, tcRate, fps)
    except Exception, e:
        print 'Could not extract timing information for ' + fpath
        f.close()
        f = None

def extract_tc(fpath):
    f = open(fpath, 'rb')
    root = extract_atoms(f)

    try:

        tcRate = extract_tcRate(root)
        drop = find_timecode_drop(root)
        tcOffset = find_timecode_fileoffset(root)
        f.seek(tcOffset)
        framessm = read_u(4, f)
        tcIn = framesToTimecode(framessm, tcRate, drop)
        fps = extract_fps(root)
        tcFrames = extract_numTcFrames(root)
        tcOut = framesToTimecode(framessm + tcFrames - 1, tcRate, drop)

        print 'Tc Rate : %d' % (tcRate)
        print 'TcIn    : %0.2d:%0.2d:%0.2d:%0.2d' % (tcIn[0], tcIn[1], tcIn[2], tcIn[3])
        print 'TcOut   : %0.2d:%0.2d:%0.2d:%0.2d' % (tcOut[0], tcOut[1], tcOut[2], tcOut[3])
        print 'Fps     : %0.3f' % (fps)

    except Exception, e:
        print 'Could not extract more timing information'

    try:
        json = extract_json(root)

        print '\nUser Metadata'
        print json
    except:
        print 'Could not extract user json'

if __name__ == "__main__":
    TEST_PATH = "P:\\vptest2\\io\\shoot_days\\incoming\\20180223_AlamedaStage02\\qtake\\raw\\BalanceBeam__1_A#ro_()_127a4f58-00000031-1.mov"
    print extract_timing(TEST_PATH)
    exit(0)
    extract_tc(TEST_PATH)
