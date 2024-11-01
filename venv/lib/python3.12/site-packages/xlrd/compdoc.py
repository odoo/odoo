# -*- coding: utf-8 -*-
# Copyright (c) 2005-2012 Stephen John Machin, Lingfo Pty Ltd
# This module is part of the xlrd package, which is released under a
# BSD-style licence.
# No part of the content of this file was derived from the works of
# David Giffin.
"""
Implements the minimal functionality required
to extract a "Workbook" or "Book" stream (as one big string)
from an OLE2 Compound Document file.
"""
from __future__ import print_function

import array
import sys
from struct import unpack

from .timemachine import *

#: Magic cookie that should appear in the first 8 bytes of the file.
SIGNATURE = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"

EOCSID = -2
FREESID = -1
SATSID = -3
MSATSID = -4
EVILSID = -5

class CompDocError(Exception):
    pass

class DirNode(object):

    def __init__(self, DID, dent, DEBUG=0, logfile=sys.stdout):
        # dent is the 128-byte directory entry
        self.DID = DID
        self.logfile = logfile
        (cbufsize, self.etype, self.colour, self.left_DID, self.right_DID,
        self.root_DID) = \
            unpack('<HBBiii', dent[64:80])
        (self.first_SID, self.tot_size) = \
            unpack('<ii', dent[116:124])
        if cbufsize == 0:
            self.name = UNICODE_LITERAL('')
        else:
            self.name = unicode(dent[0:cbufsize-2], 'utf_16_le') # omit the trailing U+0000
        self.children = [] # filled in later
        self.parent = -1 # indicates orphan; fixed up later
        self.tsinfo = unpack('<IIII', dent[100:116])
        if DEBUG:
            self.dump(DEBUG)

    def dump(self, DEBUG=1):
        fprintf(
            self.logfile,
            "DID=%d name=%r etype=%d DIDs(left=%d right=%d root=%d parent=%d kids=%r) first_SID=%d tot_size=%d\n",
            self.DID, self.name, self.etype, self.left_DID,
            self.right_DID, self.root_DID, self.parent, self.children, self.first_SID, self.tot_size
        )
        if DEBUG == 2:
            # cre_lo, cre_hi, mod_lo, mod_hi = tsinfo
            print("timestamp info", self.tsinfo, file=self.logfile)

def _build_family_tree(dirlist, parent_DID, child_DID):
    if child_DID < 0: return
    _build_family_tree(dirlist, parent_DID, dirlist[child_DID].left_DID)
    dirlist[parent_DID].children.append(child_DID)
    dirlist[child_DID].parent = parent_DID
    _build_family_tree(dirlist, parent_DID, dirlist[child_DID].right_DID)
    if dirlist[child_DID].etype == 1: # storage
        _build_family_tree(dirlist, child_DID, dirlist[child_DID].root_DID)


class CompDoc(object):
    """
    Compound document handler.

    :param mem:
      The raw contents of the file, as a string, or as an :class:`mmap.mmap`
      object. The only operation it needs to support is slicing.
    """


    def __init__(self, mem, logfile=sys.stdout, DEBUG=0, ignore_workbook_corruption=False):
        self.logfile = logfile
        self.ignore_workbook_corruption = ignore_workbook_corruption
        self.DEBUG = DEBUG
        if mem[0:8] != SIGNATURE:
            raise CompDocError('Not an OLE2 compound document')
        if mem[28:30] != b'\xFE\xFF':
            raise CompDocError('Expected "little-endian" marker, found %r' % mem[28:30])
        revision, version = unpack('<HH', mem[24:28])
        if DEBUG:
            print("\nCompDoc format: version=0x%04x revision=0x%04x" % (version, revision), file=logfile)
        self.mem = mem
        ssz, sssz = unpack('<HH', mem[30:34])
        if ssz > 20: # allows for 2**20 bytes i.e. 1MB
            print("WARNING: sector size (2**%d) is preposterous; assuming 512 and continuing ..."
                % ssz, file=logfile)
            ssz = 9
        if sssz > ssz:
            print("WARNING: short stream sector size (2**%d) is preposterous; assuming 64 and continuing ..."
                % sssz, file=logfile)
            sssz = 6
        self.sec_size = sec_size = 1 << ssz
        self.short_sec_size = 1 << sssz
        if self.sec_size != 512 or self.short_sec_size != 64:
            print("@@@@ sec_size=%d short_sec_size=%d" % (self.sec_size, self.short_sec_size), file=logfile)
        (
            SAT_tot_secs, self.dir_first_sec_sid, _unused, self.min_size_std_stream,
            SSAT_first_sec_sid, SSAT_tot_secs,
            MSATX_first_sec_sid, MSATX_tot_secs,
        ) = unpack('<iiiiiiii', mem[44:76])
        mem_data_len = len(mem) - 512
        mem_data_secs, left_over = divmod(mem_data_len, sec_size)
        if left_over:
            #### raise CompDocError("Not a whole number of sectors")
            mem_data_secs += 1
            print("WARNING *** file size (%d) not 512 + multiple of sector size (%d)"
                % (len(mem), sec_size), file=logfile)
        self.mem_data_secs = mem_data_secs # use for checking later
        self.mem_data_len = mem_data_len
        seen = self.seen = array.array('B', [0]) * mem_data_secs

        if DEBUG:
            print('sec sizes', ssz, sssz, sec_size, self.short_sec_size, file=logfile)
            print("mem data: %d bytes == %d sectors" % (mem_data_len, mem_data_secs), file=logfile)
            print("SAT_tot_secs=%d, dir_first_sec_sid=%d, min_size_std_stream=%d"
                % (SAT_tot_secs, self.dir_first_sec_sid, self.min_size_std_stream,), file=logfile)
            print("SSAT_first_sec_sid=%d, SSAT_tot_secs=%d" % (SSAT_first_sec_sid, SSAT_tot_secs,), file=logfile)
            print("MSATX_first_sec_sid=%d, MSATX_tot_secs=%d" % (MSATX_first_sec_sid, MSATX_tot_secs,), file=logfile)
        nent = sec_size // 4 # number of SID entries in a sector
        fmt = "<%di" % nent
        trunc_warned = 0
        #
        # === build the MSAT ===
        #
        MSAT = list(unpack('<109i', mem[76:512]))
        SAT_sectors_reqd = (mem_data_secs + nent - 1) // nent
        expected_MSATX_sectors = max(0, (SAT_sectors_reqd - 109 + nent - 2) // (nent - 1))
        actual_MSATX_sectors = 0
        if MSATX_tot_secs == 0 and MSATX_first_sec_sid in (EOCSID, FREESID, 0):
            # Strictly, if there is no MSAT extension, then MSATX_first_sec_sid
            # should be set to EOCSID ... FREESID and 0 have been met in the wild.
            pass # Presuming no extension
        else:
            sid = MSATX_first_sec_sid
            while sid not in (EOCSID, FREESID, MSATSID):
                # Above should be only EOCSID according to MS & OOo docs
                # but Excel doesn't complain about FREESID. Zero is a valid
                # sector number, not a sentinel.
                if DEBUG > 1:
                    print('MSATX: sid=%d (0x%08X)' % (sid, sid), file=logfile)
                if sid >= mem_data_secs:
                    msg = "MSAT extension: accessing sector %d but only %d in file" % (sid, mem_data_secs)
                    if DEBUG > 1:
                        print(msg, file=logfile)
                        break
                    raise CompDocError(msg)
                elif sid < 0:
                    raise CompDocError("MSAT extension: invalid sector id: %d" % sid)
                if seen[sid]:
                    raise CompDocError("MSAT corruption: seen[%d] == %d" % (sid, seen[sid]))
                seen[sid] = 1
                actual_MSATX_sectors += 1
                if DEBUG and actual_MSATX_sectors > expected_MSATX_sectors:
                    print("[1]===>>>", mem_data_secs, nent, SAT_sectors_reqd, expected_MSATX_sectors, actual_MSATX_sectors, file=logfile)
                offset = 512 + sec_size * sid
                MSAT.extend(unpack(fmt, mem[offset:offset+sec_size]))
                sid = MSAT.pop() # last sector id is sid of next sector in the chain

        if DEBUG and actual_MSATX_sectors != expected_MSATX_sectors:
            print("[2]===>>>", mem_data_secs, nent, SAT_sectors_reqd, expected_MSATX_sectors, actual_MSATX_sectors, file=logfile)
        if DEBUG:
            print("MSAT: len =", len(MSAT), file=logfile)
            dump_list(MSAT, 10, logfile)
        #
        # === build the SAT ===
        #
        self.SAT = []
        actual_SAT_sectors = 0
        dump_again = 0
        for msidx in xrange(len(MSAT)):
            msid = MSAT[msidx]
            if msid in (FREESID, EOCSID):
                # Specification: the MSAT array may be padded with trailing FREESID entries.
                # Toleration: a FREESID or EOCSID entry anywhere in the MSAT array will be ignored.
                continue
            if msid >= mem_data_secs:
                if not trunc_warned:
                    print("WARNING *** File is truncated, or OLE2 MSAT is corrupt!!", file=logfile)
                    print("INFO: Trying to access sector %d but only %d available"
                        % (msid, mem_data_secs), file=logfile)
                    trunc_warned = 1
                MSAT[msidx] = EVILSID
                dump_again = 1
                continue
            elif msid < -2:
                raise CompDocError("MSAT: invalid sector id: %d" % msid)
            if seen[msid]:
                raise CompDocError("MSAT extension corruption: seen[%d] == %d" % (msid, seen[msid]))
            seen[msid] = 2
            actual_SAT_sectors += 1
            if DEBUG and actual_SAT_sectors > SAT_sectors_reqd:
                print("[3]===>>>", mem_data_secs, nent, SAT_sectors_reqd, expected_MSATX_sectors, actual_MSATX_sectors, actual_SAT_sectors, msid, file=logfile)
            offset = 512 + sec_size * msid
            self.SAT.extend(unpack(fmt, mem[offset:offset+sec_size]))

        if DEBUG:
            print("SAT: len =", len(self.SAT), file=logfile)
            dump_list(self.SAT, 10, logfile)
            # print >> logfile, "SAT ",
            # for i, s in enumerate(self.SAT):
            #     print >> logfile, "entry: %4d offset: %6d, next entry: %4d" % (i, 512 + sec_size * i, s)
            #     print >> logfile, "%d:%d " % (i, s),
            print(file=logfile)
        if DEBUG and dump_again:
            print("MSAT: len =", len(MSAT), file=logfile)
            dump_list(MSAT, 10, logfile)
            for satx in xrange(mem_data_secs, len(self.SAT)):
                self.SAT[satx] = EVILSID
            print("SAT: len =", len(self.SAT), file=logfile)
            dump_list(self.SAT, 10, logfile)
        #
        # === build the directory ===
        #
        dbytes = self._get_stream(
            self.mem, 512, self.SAT, self.sec_size, self.dir_first_sec_sid,
            name="directory", seen_id=3)
        dirlist = []
        did = -1
        for pos in xrange(0, len(dbytes), 128):
            did += 1
            dirlist.append(DirNode(did, dbytes[pos:pos+128], 0, logfile))
        self.dirlist = dirlist
        _build_family_tree(dirlist, 0, dirlist[0].root_DID) # and stand well back ...
        if DEBUG:
            for d in dirlist:
                d.dump(DEBUG)
        #
        # === get the SSCS ===
        #
        sscs_dir = self.dirlist[0]
        assert sscs_dir.etype == 5 # root entry
        if sscs_dir.first_SID < 0 or sscs_dir.tot_size == 0:
            # Problem reported by Frank Hoffsuemmer: some software was
            # writing -1 instead of -2 (EOCSID) for the first_SID
            # when the SCCS was empty. Not having EOCSID caused assertion
            # failure in _get_stream.
            # Solution: avoid calling _get_stream in any case when the
            # SCSS appears to be empty.
            self.SSCS = ""
        else:
            self.SSCS = self._get_stream(
                self.mem, 512, self.SAT, sec_size, sscs_dir.first_SID,
                sscs_dir.tot_size, name="SSCS", seen_id=4)
        # if DEBUG: print >> logfile, "SSCS", repr(self.SSCS)
        #
        # === build the SSAT ===
        #
        self.SSAT = []
        if SSAT_tot_secs > 0 and sscs_dir.tot_size == 0:
            print("WARNING *** OLE2 inconsistency: SSCS size is 0 but SSAT size is non-zero", file=logfile)
        if sscs_dir.tot_size > 0:
            sid = SSAT_first_sec_sid
            nsecs = SSAT_tot_secs
            while sid >= 0 and nsecs > 0:
                if seen[sid]:
                    raise CompDocError("SSAT corruption: seen[%d] == %d" % (sid, seen[sid]))
                seen[sid] = 5
                nsecs -= 1
                start_pos = 512 + sid * sec_size
                news = list(unpack(fmt, mem[start_pos:start_pos+sec_size]))
                self.SSAT.extend(news)
                sid = self.SAT[sid]
            if DEBUG: print("SSAT last sid %d; remaining sectors %d" % (sid, nsecs), file=logfile)
            assert nsecs == 0 and sid == EOCSID
        if DEBUG:
            print("SSAT", file=logfile)
            dump_list(self.SSAT, 10, logfile)
        if DEBUG:
            print("seen", file=logfile)
            dump_list(seen, 20, logfile)

    def _get_stream(self, mem, base, sat, sec_size, start_sid, size=None, name='', seen_id=None):
        # print >> self.logfile, "_get_stream", base, sec_size, start_sid, size
        sectors = []
        s = start_sid
        if size is None:
            # nothing to check against
            while s >= 0:
                if seen_id is not None:
                    if self.seen[s]:
                        raise CompDocError("%s corruption: seen[%d] == %d" % (name, s, self.seen[s]))
                    self.seen[s] = seen_id
                start_pos = base + s * sec_size
                sectors.append(mem[start_pos:start_pos+sec_size])
                try:
                    s = sat[s]
                except IndexError:
                    raise CompDocError(
                        "OLE2 stream %r: sector allocation table invalid entry (%d)" %
                        (name, s)
                    )
            assert s == EOCSID
        else:
            todo = size
            while s >= 0:
                if seen_id is not None:
                    if self.seen[s]:
                        raise CompDocError("%s corruption: seen[%d] == %d" % (name, s, self.seen[s]))
                    self.seen[s] = seen_id
                start_pos = base + s * sec_size
                grab = sec_size
                if grab > todo:
                    grab = todo
                todo -= grab
                sectors.append(mem[start_pos:start_pos+grab])
                try:
                    s = sat[s]
                except IndexError:
                    raise CompDocError(
                        "OLE2 stream %r: sector allocation table invalid entry (%d)" %
                        (name, s)
                    )
            assert s == EOCSID
            if todo != 0:
                fprintf(self.logfile,
                    "WARNING *** OLE2 stream %r: expected size %d, actual size %d\n",
                    name, size, size - todo)

        return b''.join(sectors)

    def _dir_search(self, path, storage_DID=0):
        # Return matching DirNode instance, or None
        head = path[0]
        tail = path[1:]
        dl = self.dirlist
        for child in dl[storage_DID].children:
            if dl[child].name.lower() == head.lower():
                et = dl[child].etype
                if et == 2:
                    return dl[child]
                if et == 1:
                    if not tail:
                        raise CompDocError("Requested component is a 'storage'")
                    return self._dir_search(tail, child)
                dl[child].dump(1)
                raise CompDocError("Requested stream is not a 'user stream'")
        return None


    def get_named_stream(self, qname):
        """
        Interrogate the compound document's directory; return the stream as a
        string if found, otherwise return ``None``.

        :param qname:
          Name of the desired stream e.g. ``'Workbook'``.
          Should be in Unicode or convertible thereto.
        """
        d = self._dir_search(qname.split("/"))
        if d is None:
            return None
        if d.tot_size >= self.min_size_std_stream:
            return self._get_stream(
                self.mem, 512, self.SAT, self.sec_size, d.first_SID,
                d.tot_size, name=qname, seen_id=d.DID+6)
        else:
            return self._get_stream(
                self.SSCS, 0, self.SSAT, self.short_sec_size, d.first_SID,
                d.tot_size, name=qname + " (from SSCS)", seen_id=None)

    def locate_named_stream(self, qname):
        """
        Interrogate the compound document's directory.

        If the named stream is not found, ``(None, 0, 0)`` will be returned.

        If the named stream is found and is contiguous within the original
        byte sequence (``mem``) used when the document was opened,
        then ``(mem, offset_to_start_of_stream, length_of_stream)`` is returned.

        Otherwise a new string is built from the fragments and
        ``(new_string, 0, length_of_stream)`` is returned.

        :param qname:
          Name of the desired stream e.g. ``'Workbook'``.
          Should be in Unicode or convertible thereto.
        """
        d = self._dir_search(qname.split("/"))
        if d is None:
            return (None, 0, 0)
        if d.tot_size > self.mem_data_len:
            raise CompDocError("%r stream length (%d bytes) > file data size (%d bytes)"
                % (qname, d.tot_size, self.mem_data_len))
        if d.tot_size >= self.min_size_std_stream:
            result = self._locate_stream(
                self.mem, 512, self.SAT, self.sec_size, d.first_SID,
                d.tot_size, qname, d.DID+6)
            if self.DEBUG:
                print("\nseen", file=self.logfile)
                dump_list(self.seen, 20, self.logfile)
            return result
        else:
            return (
                self._get_stream(
                    self.SSCS, 0, self.SSAT, self.short_sec_size, d.first_SID,
                    d.tot_size, qname + " (from SSCS)", None),
                0,
                d.tot_size,
            )

    def _locate_stream(self, mem, base, sat, sec_size, start_sid, expected_stream_size, qname, seen_id):
        # print >> self.logfile, "_locate_stream", base, sec_size, start_sid, expected_stream_size
        s = start_sid
        if s < 0:
            raise CompDocError("_locate_stream: start_sid (%d) is -ve" % start_sid)
        p = -99 # dummy previous SID
        start_pos = -9999
        end_pos = -8888
        slices = []
        tot_found = 0
        found_limit = (expected_stream_size + sec_size - 1) // sec_size
        while s >= 0:
            if self.seen[s]:
                if not self.ignore_workbook_corruption:
                    print("_locate_stream(%s): seen" % qname, file=self.logfile); dump_list(self.seen, 20, self.logfile)
                    raise CompDocError("%s corruption: seen[%d] == %d" % (qname, s, self.seen[s]))
            self.seen[s] = seen_id
            tot_found += 1
            if tot_found > found_limit:
                # Note: expected size rounded up to higher sector
                raise CompDocError(
                    "%s: size exceeds expected %d bytes; corrupt?"
                    % (qname, found_limit * sec_size)
                )
            if s == p+1:
                # contiguous sectors
                end_pos += sec_size
            else:
                # start new slice
                if p >= 0:
                    # not first time
                    slices.append((start_pos, end_pos))
                start_pos = base + s * sec_size
                end_pos = start_pos + sec_size
            p = s
            s = sat[s]
        assert s == EOCSID
        assert tot_found == found_limit
        # print >> self.logfile, "_locate_stream(%s): seen" % qname; dump_list(self.seen, 20, self.logfile)
        if not slices:
            # The stream is contiguous ... just what we like!
            return (mem, start_pos, expected_stream_size)
        slices.append((start_pos, end_pos))
        # print >> self.logfile, "+++>>> %d fragments" % len(slices)
        return (b''.join(mem[start_pos:end_pos] for start_pos, end_pos in slices), 0, expected_stream_size)

# ==========================================================================================
def x_dump_line(alist, stride, f, dpos, equal=0):
    print("%5d%s" % (dpos, " ="[equal]), end=' ', file=f)
    for value in alist[dpos:dpos + stride]:
        print(str(value), end=' ', file=f)
    print(file=f)

def dump_list(alist, stride, f=sys.stdout):
    def _dump_line(dpos, equal=0):
        print("%5d%s" % (dpos, " ="[equal]), end=' ', file=f)
        for value in alist[dpos:dpos + stride]:
            print(str(value), end=' ', file=f)
        print(file=f)
    pos = None
    oldpos = None
    for pos in xrange(0, len(alist), stride):
        if oldpos is None:
            _dump_line(pos)
            oldpos = pos
        elif alist[pos:pos+stride] != alist[oldpos:oldpos+stride]:
            if pos - oldpos > stride:
                _dump_line(pos - stride, equal=1)
            _dump_line(pos)
            oldpos = pos
    if oldpos is not None and pos is not None and pos != oldpos:
        _dump_line(pos, equal=1)
