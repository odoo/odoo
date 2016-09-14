# Quick notes about binary CMap format (bcmap)

The format is designed to package some information from the CMap files located at external/cmap. Please notice for size optimization reasons, the original information blocks can be changed (split or joined) and items in the blocks can be swaped.

The data stored in binary format in network byte order (big-endian).

# Data primitives

The following primitives used during encoding of the file:
  - byte (B) – a byte, bits are numbered from 0 (less significant) to 7 (most significant)
  - bytes block (B[n])  – a sequence of n bytes
  - unsigned number (UN) – the number is encoded as sequence of bytes, bit 7 is flag to continue decoding the byte, bits 6-0 store number information, e.g. bytes 0x818407 will represent 16903 (0x4207). Limited to the 32 bit.
  - signed number (SN) – the number is encoded as sequence of bytes, as UN, however shall be transformed before encoding: if n < 0, the n shall be encoded as (-2*n-1) using UN encoding, other n shall be encoded as (2*n) using UN encoding. So the lowest bit of the number indicates the sign of the initial number
  - unsigned fixed number (UB[n]) – similar to the UN, but it represents an unsigned number that is stored in B[n]
  - signed fixed number (SB[n]) – similar to the SN, but it represents a signed number that is stored in B[n]
  - string (S) – the string is encoded as sequence of bytes. First comes length is characters encoded as UN, when UTF16 characters encoded as UN.

# File structure

The first byte is a header:
  - bits 2-1 – indicate a CMapType. Valid values are 1 and 2
  - bit 0 – indicate WMode. Valid values are 0 and 1.

Then records follow. The records starts from the record header encoded as B, where bits 7-5 indicate record type (see description of other bits below):
  - 0 – codespacerange
  - 1 – notdefrange
  - 2 – cidchar
  - 3 – cidrange
  - 4 – bfchar
  - 5 – bfrange
  - 6 – reserved
  - 7 – metadata

## Metadata record

The metadata record header bit 4-0 contain id of the metadata:
  - 0 – comment, body of the record is encoded comment string (S) 
  - 1 – UseCMap, body of the record is usecmap id string (S)

## Data records

The records that have types 0 – 5, have the following fields in the header:
  - bit 4 – indicate the char or start/end entries are stored in a sequence in this block
  - bits 3-0 – contain length of the data size minus 1 in this block (dataSize)

The amount of entries encoded as UN follows the header. The items records follow (see below).


### codespacerange (0)

Represents the following CMap block:

  n begincodespacerange
  <start> <end>
  endcodespacerange

First record format is:

  - start as B[dataSize]
  - endDelta as UB[dataSize], end is calculated as (start + endDelta)

Next record format is:

  - startDelta as UB[dataSize], start = end + startDelta
  - endDelta as UB[dataSize], end = start + endDelta


### notdefrange (1)

Represents the following CMap block:

  n beginnotdefrange
  <start> <end> code
  endnotdefrange

First record format is:

  - start as B[dataSize]
  - endDelta as UB[dataSize], end is calculated as (start + endDelta)
  - code as UN

Next record format is:

  - startDelta as UB[dataSize], start = end + startDelta
  - endDelta as UB[dataSize], end = start + endDelta
  - code as UN


### cidchar (2)

Represents the following CMap block:

  n begincidchar
  <char> code
  endcidchar

First record format is:

  - char as B[dataSize]
  - code as UN

Next record format is:

  - if sequence = 0, charDelta as UB[dataSize], char = char + charDelta + 1
  - if sequence = 1, char = char + 1
  - codeDelta as SN, code = code + codeDelta


### cidrange (3)

Represents the following CMap block:

  n begincidrange
  <start> <end> code
  endcidrange

First record format is:

  - start as B[dataSize]
  - endDelta as UN[dataSize], end is calculated as (start + endDelta)
  - code as UN

Next record format is:

  - if sequence = 0, startDelta as UB[dataSize], start = end + startDelta + 1
  - if sequence = 1, start = end + 1
  - endDelta as UN[dataSize], end = start + endDelta
  - code as UN


### bfchar (4)

Represents the following CMap block:

  n beginbfchar
  <char> <code>
  endbfchar

First record format is:

  - char as B[ucs2Size], where ucs2Size = 2 (here and below)
  - code as B[dataSize]

Next record format is:

  - if sequence = 0, charDelta as UN[ucs2Size], char = charDelta + charDelta + 1
  - if sequence = 1, char = char + 1
  - codeDelta as SB[dataSize], code = code + codeDelta


### bfrange (5)

Represents the following CMap block:

  n beginbfrange
  <start> <end> <code>
  endbfrange

First record format is:

  - start as B[ucs2Size]
  - endDelta as UB[ucs2Size], end is calculated as (start + endDelta)
  - code as B[dataSize]

Next record format is:

  - if sequence = 0, startDelta as UB[ucs2Size], start = end + startDelta + 1
  - if sequence = 1, start = end + 1
  - endDelta as UB[ucs2Size], end = start + endDelta
  - code as B[dataSize]

