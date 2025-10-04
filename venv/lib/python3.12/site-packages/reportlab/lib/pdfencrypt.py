#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
__version__='3.3.0'

"""helpers for pdf encryption/decryption"""
import sys, os
from binascii import hexlify, unhexlify
from hashlib import md5
from io import BytesIO

from reportlab.lib.utils import asBytes, int2Byte, rawBytes, asNative
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfdoc import PDFObject
from reportlab.platypus.flowables import Flowable
from reportlab import rl_config

try:
    import pyaes
    from hashlib import sha256
except ImportError:
    pyaes = None

def xorKey(num,key):
    "xor's each byte of the key with the number, which is <256"
    if num==0: return key
    return bytes(num^k for k in key)

#AR debug hooks - leaving in for now
CLOBBERID = 0  # set a constant Doc ID to allow comparison with other software like iText
CLOBBERPERMISSIONS = 0
DEBUG = rl_config.debug # print stuff to trace calculations

# permission bits
reserved1 = 1               # bit 1 must be 0
reserved2 = 1<<1            # bit 2 must be 0
printable = 1<<2
modifiable = 1<<3
copypastable = 1<<4
annotatable = 1<<5
# others [7..32] are reserved, must be 1
higherbits = 0
for i in range(6,31):
    higherbits = higherbits | (1<<i)

if rl_config.invariant:
    _os_random_x=0
    _os_random_b = b'\xbd\x8f\xdc\xabovp\xe8\x15\xec\\C\x9d\x92B~\xb8\xf4\xdeEg8\xb2f\x80Sj\'y\xcfG\xcaY\xb9\xdc-\xc4Q\x17\x88\xaf\xd1\xf7\x7f\xa1L>\x99\x89i\xf7\xc4\xb4\'\xe9k\xc9\xfa\xa6p\x80\xcd\xaa\xaf|\x97\xf7\xcc \xc1\xef\xc7\x97\xd2;\xaf\xe1\xfc\x16,\xd3\x0b\x19\xa1\x02\xe6\x01\xcb\x1c\xd8\xe6\\H}\r\xdc\x85\xe1\xbc\xc4\x02>|\xc5\x97\xb5T\xad\x0cT\x95\xb1\xdc!\xb6+E#\xa1\xa4O\xf3j\x98"\xc2\x1a\xcb\x8cHB\xd8B~\xa7\x7f7\xd2\xe8\x131.\xd7\xa9\x0b\r\xdd2\x0b}\xc0\xffm\x9e3\xe2/\xea\x84W\x82\xbd\xc8K\xc2;?\xbe#\x84`W\xf3\xe0\xec\x9e\x85\x9c\xcb\xc7\xc9#\x19\xff\xde\x17\xea\xb2\xd4\x0e\x9a\xbd\xbaz\xbd\x87O\xd4\xf4\xac\xb3(z\x92\xfc\xbc\x85i\x8d\x1f\xfb!\t|w,\x8bI\xc9_D`A\xbc}\x0e+r\x1b-%F(@\xc8\\cL\x172(\x9c\x95BM\xa1\x89UG\x9d\xfd\xed\xce\xd8\x1f\xb1'
    def os_urandom(n):
        global _os_random_x
        b = [_os_random_b[(i+_os_random_x)%256] for i in range(n)]
        b = bytes(b)
        _os_random_x = (_os_random_x + n) % 256
        return b
else:
    os_urandom = os.urandom

# no encryption
class StandardEncryption:
    prepared = 0
    def __init__(self, userPassword, ownerPassword=None, canPrint=1, canModify=1, canCopy=1, canAnnotate=1, strength=None):
        '''
        This class defines the encryption properties to be used while creating a pdf document.
        Once initiated, a StandardEncryption object can be applied to a Canvas or a BaseDocTemplate.
        The userPassword parameter sets the user password on the encrypted pdf.
        The ownerPassword parameter sets the owner password on the encrypted pdf.
        The boolean flags canPrint, canModify, canCopy, canAnnotate determine wether a user can
        perform the corresponding actions on the pdf when only a user password has been supplied.
        If the user supplies the owner password while opening the pdf, all actions can be performed regardless
        of the flags.
        Note that the security provided by these encryption settings (and even more so for the flags) is very weak.
        '''
        self.userPassword = userPassword
        if ownerPassword:
            self.ownerPassword = ownerPassword    
        else:
            self.ownerPassword = userPassword
        if strength is None:
            strength = rl_config.encryptionStrength
        if strength == 40:
            self.revision = 2
        elif strength == 128:
            self.revision = 3
        elif strength == 256:
            if not pyaes:
                raise ValueError('strength==256 is not supported as package pyaes is not importable')
            self.revision = 5
        else:
            raise ValueError('Unknown encryption strength=%s' % repr(strength))
        self.canPrint = canPrint
        self.canModify = canModify
        self.canCopy = canCopy
        self.canAnnotate = canAnnotate
        self.O = self.U = self.P = self.key = self.OE = self.UE = self.Perms =  None
    def setAllPermissions(self, value):
        self.canPrint = \
        self.canModify = \
        self.canCopy = \
        self.canAnnotate = value
    def permissionBits(self):
        p = 0
        if self.canPrint: p = p | printable
        if self.canModify: p = p | modifiable
        if self.canCopy: p = p | copypastable
        if self.canAnnotate: p = p | annotatable
        p = p | higherbits
        return p
    def encode(self, t):
        "encode a string, stream, text"
        if not self.prepared:
            raise ValueError("encryption not prepared!")
        if self.objnum is None:
            raise ValueError("not registered in PDF object")
        return encodePDF(self.key, self.objnum, self.version, t, revision=self.revision)
    def prepare(self, document, overrideID=None):
        # get ready to do encryption
        if DEBUG: print('StandardEncryption.prepare(...) - revision %d' % self.revision)
        if self.prepared:
            raise ValueError("encryption already prepared!")
        # get the unescaped string value of the document id (first array element).
        # we allow one to be passed in instead to permit reproducible tests
        # of our algorithm, but in real life overrideID will always be None
        if overrideID:
            internalID = overrideID
        else:
            externalID = document.ID() # initialize it...
            internalID = document.signature.digest()
            #AR debugging
            if CLOBBERID:
                internalID = "xxxxxxxxxxxxxxxx"

        if DEBUG:
            print('userPassword    = %r' % self.userPassword)
            print('ownerPassword   = %r' % self.ownerPassword)
            print('internalID      = %r' % internalID)
        self.P = int(self.permissionBits() - 2**31)
        if CLOBBERPERMISSIONS: self.P = -44 # AR hack
        if DEBUG:
            print("self.P          = %s" % repr(self.P))
        if self.revision == 5:
            
            # Init vectro for AES cipher (should be 16 bytes null array)
            iv  = b'\x00' * 16

            # Random User salts
            uvs = os_urandom(8)
            uks = os_urandom(8)
            
            # the main encryption key
            self.key = asBytes(os_urandom(32))
            
            if DEBUG:
                print("uvs      (hex)  = %s" % hexText(uvs))
                print("uks      (hex)  = %s" % hexText(uks))
                print("self.key (hex)  = %s" % hexText(self.key))

            # Calculate the sha-256 hash of the User password (U)
            md = sha256(asBytes(self.userPassword[:127]) + uvs)
            self.U = md.digest() + uvs + uks

            if DEBUG:
                print("self.U (hex)  = %s" % hexText(self.U))

            # Calculate the User encryption key (UE)
            md = sha256(asBytes(self.userPassword[:127]) + uks)
            
            encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(md.digest(), iv=iv))
            self.UE = encrypter.feed(self.key)
            self.UE += encrypter.feed()

            if DEBUG:
                print("self.UE (hex)  = %s" % hexText(self.UE))

            # Random Owner salts
            ovs = os_urandom(8)
            oks = os_urandom(8)

            # Calculate the hash of the Owner password (U)
            md = sha256(asBytes(self.ownerPassword[:127]) + ovs + self.U )
            self.O = md.digest() + ovs + oks

            if DEBUG:
                print("self.O (hex)  = %s" % hexText(self.O))

            # Calculate the User encryption key (OE)
            md = sha256(asBytes(self.ownerPassword[:127]) + oks + self.U)

            encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(md.digest(), iv=iv))
            self.OE = encrypter.feed(self.key)
            self.OE += encrypter.feed()

            if DEBUG:
                print("self.OE (hex)  = %s" % hexText(self.OE))

            # Compute permissions array 
            permsarr = [
                self.P       & 0xFF, # store the permission value in the first 32-bits
                self.P >> 8  & 0xFF,
                self.P >> 16 & 0xFF,
                self.P >> 24 & 0xFF,
                0xFF,
                0xFF,
                0xFF,
                0xFF,
                ord('T'),             # 'T' if EncryptMetaData is True (default), 'F' otherwise
                ord('a'),             # a, d, b are magic values 
                ord('d'),
                ord('b'),
                0x01,                   # trailing zeros will be ignored
                0x01,
                0x01,
                0x01
            ]

            # the permission array should be enrypted in the Perms field
            encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(self.key, iv=iv))
            self.Perms = encrypter.feed(bytes(permsarr))
            self.Perms += encrypter.feed()
                        
            if DEBUG:
                print("self.Perms (hex)  = %s" % hexText(self.Perms))

        elif self.revision in (2, 3):
            self.O = computeO(self.userPassword, self.ownerPassword, self.revision)

            if DEBUG:
                print("self.O (as hex) = %s" % hexText(self.O))

            #print "\nself.O", self.O, repr(self.O)
            self.key = encryptionkey(self.userPassword, self.O, self.P, internalID, revision=self.revision)
            if DEBUG:
                print("self.key (hex)  = %s" % hexText(self.key))
            self.U = computeU(self.key, revision=self.revision, documentId=internalID)
            if DEBUG:
                print("self.U (as hex) = %s" % hexText(self.U))

        self.objnum = self.version = None
        self.prepared = 1
    def register(self, objnum, version):
        # enter a new direct object
        if not self.prepared:
            raise ValueError("encryption not prepared!")
        self.objnum = objnum
        self.version = version
    def info(self):
        # the representation of self in file if any (should be None or PDFDict)
        if not self.prepared:
            raise ValueError("encryption not prepared!")
        return StandardEncryptionDictionary(O=self.O, OE=self.OE, U=self.U, UE=self.UE, P=self.P, Perms=self.Perms, revision=self.revision)

class StandardEncryptionDictionary(PDFObject):
    __RefOnly__ = 1
    def __init__(self, O, OE, U, UE,  P, Perms, revision):
        self.O,  self.OE, self.U, self.UE, self.P, self.Perms = O, OE, U, UE, P, Perms
        self.revision = revision
    def format(self, document):
        # use a dummy document to bypass encryption
        from reportlab.pdfbase.pdfdoc import DummyDoc, PDFDictionary, PDFName
        dummy = DummyDoc()
        dict = {"Filter": PDFName("Standard"),
                "O": hexText(self.O),
                "U": hexText(self.U),
                "P": self.P}
        if self.revision == 5:
            dict['Length'] = 256
            dict['R'] = 5
            dict['V'] = 5
            dict['O'] = hexText(self.O)
            dict['U'] = hexText(self.U)
            dict['OE'] = hexText(self.OE)
            dict['UE'] = hexText(self.UE)
            dict['Perms'] = hexText(self.Perms)
            dict['StrF'] = PDFName("StdCF")
            dict['StmF'] = PDFName("StdCF")
            stdcf = {
                "Length": 32,
                "AuthEvent": PDFName("DocOpen"),
                "CFM": PDFName("AESV3")
            }
            cf = {
                "StdCF": PDFDictionary(stdcf)
            }

            dict['CF'] = PDFDictionary(cf)

        elif self.revision == 3:
            dict['Length'] = 128
            dict['R'] = 3
            dict['V'] = 2
        else:
            dict['R'] = 2
            dict['V'] = 1
        pdfdict = PDFDictionary(dict)
        return pdfdict.format(dummy)

# from pdf spec
padding = """
28 BF 4E 5E 4E 75 8A 41 64 00 4E 56 FF FA 01 08
2E 2E 00 B6 D0 68 3E 80 2F 0C A9 FE 64 53 69 7A
"""

def hexText(text):
    "a legitimate way to show strings in PDF"
    return '<%s>' % asNative(hexlify(rawBytes(text))).upper()

def unHexText(hexText):
    equalityCheck(hexText[0], '<', 'bad hex text')
    equalityCheck(hexText[-1], '>', 'bad hex text')
    return unhexlify(hexText[1:-1])

PadString = rawBytes(''.join(chr(int(c, 16)) for c in padding.strip().split()))

def checkRevision(revision):
    if revision is None:
        strength = rl_config.encryptionStrength
        if strength == 40:
            revision = 2
        elif strength == 128:
            revision = 3
        elif strength == 256:
            if not pyaes:
                raise ValueError('strength==256 is not supported as package pyaes is not importable')
            revision = 5
        else:
            raise ValueError('Unknown encryption strength=%s' % repr(strength))
    return revision

def encryptionkey(password, OwnerKey, Permissions, FileId1, revision=None):
    revision = checkRevision(revision)
    # FileId1 is first string of the fileid array
    # add padding string
    #AR force same as iText example
    #Permissions =  -1836   #int(Permissions - 2**31)
    password = asBytes(password) + PadString
    # truncate to 32 bytes
    password = password[:32]
    # translate permissions to string, low order byte first
    p = Permissions# + 2**32L
    permissionsString = b""
    for i in range(4):
        byte = (p & 0xff)    # seems to match what iText does
        p = p>>8
        permissionsString += int2Byte(byte % 256)

    hash = md5(asBytes(password))
    hash.update(asBytes(OwnerKey))
    hash.update(asBytes(permissionsString))
    hash.update(asBytes(FileId1))

    md5output = hash.digest()

    if revision==2:
        key = md5output[:5]
    elif revision==3:  #revision 3 algorithm - loop 50 times
        for x in range(50):
            md5output = md5(md5output).digest()
        key = md5output[:16]
    if DEBUG: print('encryptionkey(%s,%s,%s,%s,%s)==>%s' % tuple([hexText(str(x)) for x in (password, OwnerKey, Permissions, FileId1, revision, key)]))
    return key

def computeO(userPassword, ownerPassword, revision):
    from reportlab.lib.arciv import ArcIV
    #print 'digest of hello is %s' % md5('hello').digest()
    assert revision in (2,3), 'Unknown algorithm revision %s' % revision
    if not ownerPassword:
        ownerPassword = userPassword

    ownerPad = asBytes(ownerPassword) + PadString
    ownerPad = ownerPad[0:32]

    password = asBytes(userPassword) + PadString
    userPad = password[:32]

    digest = md5(ownerPad).digest()
    if DEBUG: print('PadString=%s\nownerPad=%s\npassword=%s\nuserPad=%s\ndigest=%s\nrevision=%s' % (ascii(PadString),ascii(ownerPad),ascii(password),ascii(userPad),ascii(digest),revision))
    if revision == 2:
        O = ArcIV(digest[:5]).encode(userPad)
    elif revision == 3:
        for i in range(50):
            digest = md5(digest).digest()
        digest = digest[:16]
        O = userPad
        for i in range(20):
            thisKey = xorKey(i, digest)
            O = ArcIV(thisKey).encode(O)
    if DEBUG: print('computeO(%s,%s,%s)==>%s' % tuple([hexText(str(x)) for x in (userPassword, ownerPassword, revision,O)]))
    return O

def computeU(encryptionkey, encodestring=PadString,revision=None,documentId=None):
    revision = checkRevision(revision)
    from reportlab.lib.arciv import ArcIV
    if revision == 2:
        result = ArcIV(encryptionkey).encode(encodestring)
    elif revision == 3:
        assert documentId is not None, "Revision 3 algorithm needs the document ID!"
        h = md5(PadString)
        h.update(rawBytes(documentId))
        tmp = h.digest()
        tmp = ArcIV(encryptionkey).encode(tmp)
        for n in range(1,20):
            thisKey = xorKey(n, encryptionkey)
            tmp = ArcIV(thisKey).encode(tmp)
        while len(tmp) < 32:
            tmp += b'\0'
        result = tmp
    if DEBUG: print('computeU(%s,%s,%s,%s)==>%s' % tuple([hexText(str(x)) for x in (encryptionkey, encodestring,revision,documentId,result)]))
    return result

def checkU(encryptionkey, U):
    decoded = computeU(encryptionkey, U)
    #print len(decoded), len(U), len(PadString)
    if decoded!=PadString:
        if len(decoded)!=len(PadString):
            raise ValueError("lengths don't match! (password failed)")
        raise ValueError("decode of U doesn't match fixed padstring (password failed)")

def encodePDF(key, objectNumber, generationNumber, string, revision=None):
    "Encodes a string or stream"
    revision = checkRevision(revision)
    #print 'encodePDF (%s, %d, %d, %s)' % (hexText(key), objectNumber, generationNumber, string)
    # extend 3 bytes of the object Number, low byte first
    if revision in (2,3):
        newkey = key
        n = objectNumber
        for i in range(3):
            newkey += int2Byte(n & 0xff)
            n = n>>8
        # extend 2 bytes of the generationNumber
        n = generationNumber
        for i in range(2):
            newkey += int2Byte(n & 0xff)
            n = n>>8
        md5output = md5(newkey).digest()
        if revision == 2:
            key = md5output[:10]
        elif revision == 3:
            key = md5output #all 16 bytes
        from reportlab.lib.arciv import ArcIV
        encrypted = ArcIV(key).encode(string)
        #print 'encrypted=', hexText(encrypted)
    elif revision == 5:
        iv = os_urandom(16)
        encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(key, iv=iv))
       
        # pkcs7 style padding so that the size of the encrypted block is multiple of 16 
        string_len = len(string)
        padding = ""
        padding_len = (16 - (string_len % 16)) if string_len > 16 else (16 - string_len)
        if padding_len > 0:
            padding = chr(padding_len) * padding_len
            
        if isinstance(string, str):
            string = (string + padding).encode("utf-8")    
        else:
            string += asBytes(padding)
            
        encrypted = iv + encrypter.feed(string)
        encrypted += encrypter.feed()

    if DEBUG: print('encodePDF(%s,%s,%s,%s,%s)==>%s' % tuple([hexText(str(x)) for x in (key, objectNumber, generationNumber, string, revision,encrypted)]))
    return encrypted

def equalityCheck(observed,expected,label):
    assert observed==expected,'%s\n expected=%s\n observed=%s' % (label,expected,observed)
######################################################################
#
#  quick tests of algorithm, should be moved elsewhere
#
######################################################################
def test():
    # do a 40 bit example known to work in Acrobat Reader 4.0
    enc = StandardEncryption('User','Owner', strength=40)
    enc.prepare(None, overrideID='xxxxxxxxxxxxxxxx')

    expectedO = '<FA7F558FACF8205D25A7F1ABFA02629F707AE7B0211A2BB26F5DF4C30F684301>'
    expectedU = '<09F26CF46190AF8F93B304AD50C16B615DC43C228C9B2D2EA34951A80617B2B1>'
    expectedKey = '<BB2C00EB3D>'    # 5 byte key = 40 bits

    equalityCheck(hexText(enc.O),expectedO, '40 bit O value')
    equalityCheck(hexText(enc.U),expectedU, '40 bit U value')
    equalityCheck(hexText(enc.key),expectedKey, '40 bit key value')

    # now for 128 bit example
    enc = StandardEncryption('userpass','ownerpass', strength=128)
    enc.prepare(None, overrideID = 'xxxxxxxxxxxxxxxx')

    expectedO = '<68E5704AC779A5F0CD89704406587A52F25BF61CADC56A0F8DB6C4DB0052534D>'
    expectedU = '<A9AE45CDE827FE0B7D6536267948836A00000000000000000000000000000000>'
    expectedKey = '<13DDE7585D9BE366C976DDD56AF541D1>'  # 16 byte key = 128 bits

    equalityCheck(hexText(enc.O), expectedO, '128 bit O value')
    equalityCheck(hexText(enc.U), expectedU, '128 bit U value')
    equalityCheck(hexText(enc.key), expectedKey, '128 key value')

    ######################################################################
    #
    #  These represent the higher level API functions
    #
    ######################################################################

def encryptCanvas(canvas,
                  userPassword, ownerPassword=None,
                  canPrint=1, canModify=1, canCopy=1, canAnnotate=1,
                  strength=40):
    "Applies encryption to the document being generated"

    enc = StandardEncryption(userPassword, ownerPassword,
                             canPrint, canModify, canCopy, canAnnotate,
                             strength=strength)
    canvas._doc.encrypt = enc

# Platypus stuff needs work, sadly.  I wanted to do it without affecting
# needing changes to latest release.
class EncryptionFlowable(StandardEncryption, Flowable):
    """Drop this in your Platypus story and it will set up the encryption options.

    If you do it multiple times, the last one before saving will win."""

    def wrap(self, availWidth, availHeight):
        return (0,0)

    def draw(self):
        encryptCanvas(self.canv,
                      self.userPassword,
                      self.ownerPassword,
                      self.canPrint,
                      self.canModify,
                      self.canCopy,
                      self.canAnnotate)

##  I am thinking about this one.  Needs a change to reportlab to
##  work.
def encryptDocTemplate(dt,
                  userPassword, ownerPassword=None,
                  canPrint=1, canModify=1, canCopy=1, canAnnotate=1,
                       strength=40):
    "For use in Platypus.  Call before build()."
    raise Exception("Not implemented yet")


def encryptPdfInMemory(inputPDF,
                  userPassword, ownerPassword=None,
                  canPrint=1, canModify=1, canCopy=1, canAnnotate=1,
                       strength=40):
    """accepts a PDF file 'as a byte array in memory'; return encrypted one.

    This is a high level convenience and does not touch the hard disk in any way.
    If you are encrypting the same file over and over again, it's better to use
    pageCatcher and cache the results."""

    try:
        from rlextra.pageCatcher.pageCatcher import storeFormsInMemory, restoreFormsInMemory
    except ImportError:
        raise ImportError('''reportlab.lib.pdfencrypt.encryptPdfInMemory failed because rlextra cannot be imported.
See https://www.reportlab.com/downloads''')

    (bboxInfo, pickledForms) = storeFormsInMemory(inputPDF, all=1, BBoxes=1)
    names = list(bboxInfo.keys())

    firstPageSize = bboxInfo['PageForms0'][2:]

    #now make a new PDF document
    buf = BytesIO()
    canv = Canvas(buf, pagesize=firstPageSize)

    # set a standard ID while debugging
    if CLOBBERID:
        canv._doc._ID = "[(xxxxxxxxxxxxxxxx)(xxxxxxxxxxxxxxxx)]"

    formNames = restoreFormsInMemory(pickledForms, canv)
    for formName in formNames:
        canv.setPageSize(bboxInfo[formName][2:])
        canv.doForm(formName)
        canv.showPage()
    encryptCanvas(canv,
                  userPassword, ownerPassword,
                  canPrint, canModify, canCopy, canAnnotate,
                  strength=strength)
    canv.save()
    return buf.getvalue()

def encryptPdfOnDisk(inputFileName, outputFileName,
                  userPassword, ownerPassword=None,
                  canPrint=1, canModify=1, canCopy=1, canAnnotate=1,
                     strength=40):
    "Creates encrypted file OUTPUTFILENAME.  Returns size in bytes."

    inputPDF = open(inputFileName, 'rb').read()
    outputPDF = encryptPdfInMemory(inputPDF,
                  userPassword, ownerPassword,
                  canPrint, canModify, canCopy, canAnnotate,
                                   strength=strength)
    open(outputFileName, 'wb').write(outputPDF)
    return len(outputPDF)


def scriptInterp():
    sys_argv = sys.argv[:] # copy

    usage = """PDFENCRYPT USAGE:

PdfEncrypt encrypts your PDF files.

Line mode usage:

% pdfencrypt.exe pdffile [-o ownerpassword] | [owner ownerpassword],
\t[-u userpassword] | [user userpassword],
\t[-p 1|0] | [printable 1|0],
\t[-m 1|0] | [modifiable 1|0],
\t[-c 1|0] | [copypastable 1|0],
\t[-a 1|0] | [annotatable 1|0],
\t[-s savefilename] | [savefile savefilename],
\t[-v 1|0] | [verbose 1|0],
\t[-e128], [encrypt128],
\t[-h] | [help]

-o or owner set the owner password.
-u or user set the user password.
-p or printable set the printable attribute (must be 1 or 0).
-m or modifiable sets the modifiable attribute (must be 1 or 0).
-c or copypastable sets the copypastable attribute (must be 1 or 0).
-a or annotatable sets the annotatable attribute (must be 1 or 0).
-s or savefile sets the name for the output PDF file
-v or verbose prints useful output to the screen.
      (this defaults to 'pdffile_encrypted.pdf').
'-e128' or 'encrypt128' allows you to use 128 bit encryption (in beta).
'-e256' or 'encrypt256' allows you to use 256 bit encryption (in beta AES).

-h or help prints this message.

See PdfEncryptIntro.pdf for more information.
"""

    known_modes = ['-o', 'owner',
                   '-u', 'user',
                   '-p', 'printable',
                   '-m', 'modifiable',
                   '-c', 'copypastable',
                   '-a', 'annotatable',
                   '-s', 'savefile',
                   '-v', 'verbose',
                   '-h', 'help',
                   '-e128', 'encrypt128',
                   '-e256', 'encryptAES',
                   ]

    OWNER        = ''
    USER         = ''
    PRINTABLE    = 1
    MODIFIABLE   = 1
    COPYPASTABLE = 1
    ANNOTATABLE  = 1
    SAVEFILE     = 'encrypted.pdf'

    #try:
    caller = sys_argv[0] # may be required later - eg if called by security.py
    argv = list(sys_argv)[1:]
    if len(argv)>0:
        if argv[0] == '-h' or argv[0] == 'help':
            print(usage)
            return
        if len(argv)<2:
            raise ValueError("Must include a filename and one or more arguments!")
        if argv[0] not in known_modes:
            infile = argv[0]
            argv = argv[1:]
            if not os.path.isfile(infile):
                raise ValueError("Can't open input file '%s'!" % infile)
        else:
            raise ValueError("First argument must be name of the PDF input file!")

        # meaningful name at this stage
        STRENGTH = 40
        for (s,_a) in ((128,('-e128','encrypt128')),(256,('-e256','encrypt256'))):
            for a in _a:
                if a in argv:
                    STRENGTH = s
                    argv.remove(a)

        if ('-v' in argv) or ('verbose' in argv):
            if '-v' in argv:
                pos = argv.index('-v')
                arg = "-v"
            elif 'verbose' in argv:
                pos = argv.index('verbose')
                arg = "verbose"
            try:
                verbose = int(argv[pos+1])
            except:
                verbose = 1
            argv.remove(argv[pos+1])
            argv.remove(arg)
        else:
            from reportlab.rl_config import verbose

        #argument, valid license variable, invalid license variable, text for print
        arglist = (('-o', 'OWNER', OWNER, 'Owner password'),
                   ('owner', 'OWNER', OWNER, 'Owner password'),
                   ('-u', 'USER', USER, 'User password'),
                   ('user', 'USER', USER, 'User password'),
                   ('-p', 'PRINTABLE', PRINTABLE, "'Printable'"),
                   ('printable', 'PRINTABLE', PRINTABLE, "'Printable'"),
                   ('-m', 'MODIFIABLE', MODIFIABLE, "'Modifiable'"),
                   ('modifiable', 'MODIFIABLE',  MODIFIABLE, "'Modifiable'"),
                   ('-c', 'COPYPASTABLE', COPYPASTABLE, "'Copypastable'"),
                   ('copypastable', 'COPYPASTABLE', COPYPASTABLE, "'Copypastable'"),
                   ('-a', 'ANNOTATABLE', ANNOTATABLE, "'Annotatable'"),
                   ('annotatable', 'ANNOTATABLE', ANNOTATABLE, "'Annotatable'"),
                   ('-s', 'SAVEFILE', SAVEFILE, "Output file"),
                   ('savefile', 'SAVEFILE', SAVEFILE, "Output file"),
                   )

        binaryrequired = ('-p', 'printable', '-m', 'modifiable', 'copypastable', '-c', 'annotatable', '-a')

        for thisarg in arglist:
            if thisarg[0] in argv:
                pos = argv.index(thisarg[0])
                if thisarg[0] in binaryrequired:
                    if argv[pos+1] not in ('1', '0'):
                        raise ValueError("%s value must be either '1' or '0'!" % thisarg[1])
                try:
                    if argv[pos+1] not in known_modes:
                        if thisarg[0] in binaryrequired:
                            exec(thisarg[1] +' = int(argv[pos+1])',vars())
                        else:
                            exec(thisarg[1] +' = argv[pos+1]',vars())
                        if verbose:
                            print("%s set to: '%s'." % (thisarg[3], argv[pos+1]))
                        argv.remove(argv[pos+1])
                        argv.remove(thisarg[0])
                except:
                    raise "Unable to set %s." % thisarg[3]

        if verbose>4:
            #useful if feeling paranoid and need to double check things at this point...
            print("\ninfile:", infile)
            print("STRENGTH:", STRENGTH)
            print("SAVEFILE:", SAVEFILE)
            print("USER:", USER)
            print("OWNER:", OWNER)
            print("PRINTABLE:", PRINTABLE)
            print("MODIFIABLE:", MODIFIABLE)
            print("COPYPASTABLE:", COPYPASTABLE)
            print("ANNOTATABLE:", ANNOTATABLE)
            print("SAVEFILE:", SAVEFILE)
            print("VERBOSE:", verbose)


        if SAVEFILE == 'encrypted.pdf':
            if infile[-4:] == '.pdf' or infile[-4:] == '.PDF':
                tinfile = infile[:-4]
            else:
                tinfile = infile
            SAVEFILE = tinfile+"_encrypted.pdf"

        filesize = encryptPdfOnDisk(infile, SAVEFILE, USER, OWNER,
                  PRINTABLE, MODIFIABLE, COPYPASTABLE, ANNOTATABLE,
                                    strength=STRENGTH)

        if verbose:
            print("wrote output file '%s'(%s bytes)\n  owner password is '%s'\n  user password is '%s'" % (SAVEFILE, filesize, OWNER, USER))

        if len(argv)>0:
            raise ValueError("\nUnrecognised arguments : %s\nknown arguments are:\n%s" % (str(argv)[1:-1], known_modes))
    else:
        print(usage)

def main():
    scriptInterp()

if __name__=="__main__": #NO RUNTESTS
    a = [x for x in sys.argv if x[:7]=='--debug']
    if a:
        sys.argv = [x for x in sys.argv if x[:7]!='--debug']
        DEBUG = len(a)
    if '--test' in sys.argv: test()
    else: main()
