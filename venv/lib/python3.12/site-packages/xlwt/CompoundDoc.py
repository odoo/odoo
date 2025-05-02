# -*- coding: windows-1252 -*-

import struct
from .compat import xrange
        
# This implementation writes only 'Root Entry', 'Workbook' streams
# and 2 empty streams for aligning directory stream on sector boundary
# 
# LAYOUT:
# 0         header
# 76                MSAT (1st part: 109 SID)
# 512       workbook stream
# ...       additional MSAT sectors if streams' size > about 7 Mb == (109*512 * 128)
# ...       SAT
# ...       directory stream
#
# NOTE: this layout is "ad hoc". It can be more general. RTFM

class XlsDoc:
    SECTOR_SIZE = 0x0200
    MIN_LIMIT   = 0x1000

    SID_FREE_SECTOR  = -1
    SID_END_OF_CHAIN = -2
    SID_USED_BY_SAT  = -3
    SID_USED_BY_MSAT = -4

    def __init__(self):
        #self.book_stream = ''                # padded
        self.book_stream_sect = []

        self.dir_stream = ''
        self.dir_stream_sect = []

        self.packed_SAT = ''
        self.SAT_sect = []

        self.packed_MSAT_1st = ''
        self.packed_MSAT_2nd = ''
        self.MSAT_sect_2nd = []

        self.header = ''

    def _build_directory(self): # align on sector boundary
        self.dir_stream = b''

        dentry_name      = u'Root Entry\x00'.encode('utf-16-le')
        dentry_name_sz   = len(dentry_name)
        dentry_name_pad  = b'\x00'*(64 - dentry_name_sz)
        dentry_type      = 0x05 # root storage
        dentry_colour    = 0x01 # black
        dentry_did_left  = -1
        dentry_did_right = -1
        dentry_did_root  = 1
        dentry_start_sid = -2
        dentry_stream_sz = 0

        self.dir_stream += struct.pack('<64s H 2B 3l 9L l L L',
           dentry_name + dentry_name_pad,
           dentry_name_sz,
           dentry_type,
           dentry_colour,
           dentry_did_left, 
           dentry_did_right,
           dentry_did_root,
           0, 0, 0, 0, 0, 0, 0, 0, 0,
           dentry_start_sid,
           dentry_stream_sz,
           0
        )

        dentry_name      = u'Workbook\x00'.encode('utf-16-le')
        dentry_name_sz   = len(dentry_name)
        dentry_name_pad  = b'\x00'*(64 - dentry_name_sz)
        dentry_type      = 0x02 # user stream
        dentry_colour    = 0x01 # black
        dentry_did_left  = -1
        dentry_did_right = -1
        dentry_did_root  = -1
        dentry_start_sid = 0     
        dentry_stream_sz = self.book_stream_len

        self.dir_stream += struct.pack('<64s H 2B 3l 9L l L L',
           dentry_name + dentry_name_pad,
           dentry_name_sz,
           dentry_type,
           dentry_colour,
           dentry_did_left, 
           dentry_did_right,
           dentry_did_root,
           0, 0, 0, 0, 0, 0, 0, 0, 0, 
           dentry_start_sid,
           dentry_stream_sz,
           0
        )
        
        # padding
        dentry_name      = b''
        dentry_name_sz   = len(dentry_name)
        dentry_name_pad  = b'\x00'*(64 - dentry_name_sz)
        dentry_type      = 0x00 # empty
        dentry_colour    = 0x01 # black
        dentry_did_left  = -1
        dentry_did_right = -1
        dentry_did_root  = -1
        dentry_start_sid = -2
        dentry_stream_sz = 0

        self.dir_stream += struct.pack('<64s H 2B 3l 9L l L L',
           dentry_name + dentry_name_pad,
           dentry_name_sz,
           dentry_type,
           dentry_colour,
           dentry_did_left, 
           dentry_did_right,
           dentry_did_root,
           0, 0, 0, 0, 0, 0, 0, 0, 0,
           dentry_start_sid,
           dentry_stream_sz,
           0
        ) * 2
    
    def _build_sat(self):
        # Build SAT
        book_sect_count = self.book_stream_len >> 9
        dir_sect_count  = len(self.dir_stream) >> 9
        
        total_sect_count     = book_sect_count + dir_sect_count
        SAT_sect_count       = 0
        MSAT_sect_count      = 0
        SAT_sect_count_limit = 109
        while total_sect_count > 128*SAT_sect_count or SAT_sect_count > SAT_sect_count_limit:
            SAT_sect_count   += 1
            total_sect_count += 1
            if SAT_sect_count > SAT_sect_count_limit:
                MSAT_sect_count      += 1
                total_sect_count     += 1
                SAT_sect_count_limit += 127


        SAT = [self.SID_FREE_SECTOR]*128*SAT_sect_count

        sect = 0
        while sect < book_sect_count - 1:
            self.book_stream_sect.append(sect)
            SAT[sect] = sect + 1
            sect += 1
        self.book_stream_sect.append(sect)
        SAT[sect] = self.SID_END_OF_CHAIN
        sect += 1

        while sect < book_sect_count + MSAT_sect_count:
            self.MSAT_sect_2nd.append(sect)
            SAT[sect] = self.SID_USED_BY_MSAT
            sect += 1

        while sect < book_sect_count + MSAT_sect_count + SAT_sect_count:
            self.SAT_sect.append(sect)            
            SAT[sect] = self.SID_USED_BY_SAT
            sect += 1

        while sect < book_sect_count + MSAT_sect_count + SAT_sect_count + dir_sect_count - 1:
            self.dir_stream_sect.append(sect)
            SAT[sect] = sect + 1
            sect += 1
        self.dir_stream_sect.append(sect)
        SAT[sect] = self.SID_END_OF_CHAIN
        sect += 1

        self.packed_SAT = struct.pack('<%dl' % (SAT_sect_count*128), *SAT)

        MSAT_1st = [self.SID_FREE_SECTOR]*109
        for i, SAT_sect_num in zip(range(0, 109), self.SAT_sect):
            MSAT_1st[i] = SAT_sect_num
        self.packed_MSAT_1st = struct.pack('<109l', *MSAT_1st)

        MSAT_2nd = [self.SID_FREE_SECTOR]*128*MSAT_sect_count
        if MSAT_sect_count > 0:
            MSAT_2nd[- 1] = self.SID_END_OF_CHAIN

        i = 109
        msat_sect = 0
        sid_num = 0
        while i < SAT_sect_count:
            if (sid_num + 1) % 128 == 0:
                #print 'link: ',
                msat_sect += 1
                if msat_sect < len(self.MSAT_sect_2nd):
                    MSAT_2nd[sid_num] = self.MSAT_sect_2nd[msat_sect]
            else:
                #print 'sid: ',
                MSAT_2nd[sid_num] = self.SAT_sect[i]
                i += 1
            #print sid_num, MSAT_2nd[sid_num]
            sid_num += 1

        self.packed_MSAT_2nd = struct.pack('<%dl' % (MSAT_sect_count*128), *MSAT_2nd)

        #print vars()
        #print zip(range(0, sect), SAT)
        #print self.book_stream_sect
        #print self.MSAT_sect_2nd
        #print MSAT_2nd
        #print self.SAT_sect
        #print self.dir_stream_sect


    def _build_header(self):
        doc_magic             = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
        file_uid              = b'\x00'*16
        rev_num               = b'\x3E\x00'
        ver_num               = b'\x03\x00'
        byte_order            = b'\xFE\xFF'
        log_sect_size         = struct.pack('<H', 9)
        log_short_sect_size   = struct.pack('<H', 6)
        not_used0             = b'\x00'*10
        total_sat_sectors     = struct.pack('<L', len(self.SAT_sect))
        dir_start_sid         = struct.pack('<l', self.dir_stream_sect[0])
        not_used1             = b'\x00'*4
        min_stream_size       = struct.pack('<L', 0x1000)
        ssat_start_sid        = struct.pack('<l', -2)
        total_ssat_sectors    = struct.pack('<L', 0)

        if len(self.MSAT_sect_2nd) == 0:
            msat_start_sid        = struct.pack('<l', -2)
        else:
            msat_start_sid        = struct.pack('<l', self.MSAT_sect_2nd[0])

        total_msat_sectors    = struct.pack('<L', len(self.MSAT_sect_2nd))

        self.header =       b''.join([  doc_magic,
                                        file_uid,
                                        rev_num,
                                        ver_num,
                                        byte_order,
                                        log_sect_size,
                                        log_short_sect_size,
                                        not_used0,
                                        total_sat_sectors,
                                        dir_start_sid,
                                        not_used1,
                                        min_stream_size,
                                        ssat_start_sid,
                                        total_ssat_sectors,
                                        msat_start_sid,
                                        total_msat_sectors
                                    ])
                                        

    def save(self, file_name_or_filelike_obj, stream):
        # 1. Align stream on 0x1000 boundary (and therefore on sector boundary)
        padding = b'\x00' * (0x1000 - (len(stream) % 0x1000))
        self.book_stream_len = len(stream) + len(padding)

        self._build_directory()
        self._build_sat()
        self._build_header()
        
        f = file_name_or_filelike_obj
        we_own_it = not hasattr(f, 'write')
        if we_own_it:
            f = open(file_name_or_filelike_obj, 'w+b')
        f.write(self.header)
        f.write(self.packed_MSAT_1st)
        # There are reports of large writes failing when writing to "network shares" on Windows.
        # MS says in KB899149 that it happens at 32KB less than 64MB.
        # This is said to be alleviated by using "w+b" mode instead of "wb".
        # One xlwt user has reported anomalous results at much smaller sizes,
        # The fallback is to write the stream in 4 MB chunks.
        try:
            f.write(stream)
        except IOError as e:
            if e.errno != 22: # "Invalid argument" i.e. 'stream' is too big
                raise # some other problem
            chunk_size = 4 * 1024 * 1024
            for offset in xrange(0, len(stream), chunk_size):
                f.write(buffer(stream, offset, chunk_size))
        f.write(padding)
        f.write(self.packed_MSAT_2nd)
        f.write(self.packed_SAT)
        f.write(self.dir_stream)
        if we_own_it:
            f.close()
