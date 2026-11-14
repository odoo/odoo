# coding: utf-8

"""
Implementation of the teletex T.61 codec. Exports the following items:

 - register()
"""

from __future__ import unicode_literals, division, absolute_import, print_function

import codecs


class TeletexCodec(codecs.Codec):

    def encode(self, input_, errors='strict'):
        return codecs.charmap_encode(input_, errors, ENCODING_TABLE)

    def decode(self, input_, errors='strict'):
        return codecs.charmap_decode(input_, errors, DECODING_TABLE)


class TeletexIncrementalEncoder(codecs.IncrementalEncoder):

    def encode(self, input_, final=False):
        return codecs.charmap_encode(input_, self.errors, ENCODING_TABLE)[0]


class TeletexIncrementalDecoder(codecs.IncrementalDecoder):

    def decode(self, input_, final=False):
        return codecs.charmap_decode(input_, self.errors, DECODING_TABLE)[0]


class TeletexStreamWriter(TeletexCodec, codecs.StreamWriter):

    pass


class TeletexStreamReader(TeletexCodec, codecs.StreamReader):

    pass


def teletex_search_function(name):
    """
    Search function for teletex codec that is passed to codecs.register()
    """

    if name != 'teletex':
        return None

    return codecs.CodecInfo(
        name='teletex',
        encode=TeletexCodec().encode,
        decode=TeletexCodec().decode,
        incrementalencoder=TeletexIncrementalEncoder,
        incrementaldecoder=TeletexIncrementalDecoder,
        streamreader=TeletexStreamReader,
        streamwriter=TeletexStreamWriter,
    )


def register():
    """
    Registers the teletex codec
    """

    codecs.register(teletex_search_function)


# http://en.wikipedia.org/wiki/ITU_T.61
DECODING_TABLE = (
    '\u0000'
    '\u0001'
    '\u0002'
    '\u0003'
    '\u0004'
    '\u0005'
    '\u0006'
    '\u0007'
    '\u0008'
    '\u0009'
    '\u000A'
    '\u000B'
    '\u000C'
    '\u000D'
    '\u000E'
    '\u000F'
    '\u0010'
    '\u0011'
    '\u0012'
    '\u0013'
    '\u0014'
    '\u0015'
    '\u0016'
    '\u0017'
    '\u0018'
    '\u0019'
    '\u001A'
    '\u001B'
    '\u001C'
    '\u001D'
    '\u001E'
    '\u001F'
    '\u0020'
    '\u0021'
    '\u0022'
    '\ufffe'
    '\ufffe'
    '\u0025'
    '\u0026'
    '\u0027'
    '\u0028'
    '\u0029'
    '\u002A'
    '\u002B'
    '\u002C'
    '\u002D'
    '\u002E'
    '\u002F'
    '\u0030'
    '\u0031'
    '\u0032'
    '\u0033'
    '\u0034'
    '\u0035'
    '\u0036'
    '\u0037'
    '\u0038'
    '\u0039'
    '\u003A'
    '\u003B'
    '\u003C'
    '\u003D'
    '\u003E'
    '\u003F'
    '\u0040'
    '\u0041'
    '\u0042'
    '\u0043'
    '\u0044'
    '\u0045'
    '\u0046'
    '\u0047'
    '\u0048'
    '\u0049'
    '\u004A'
    '\u004B'
    '\u004C'
    '\u004D'
    '\u004E'
    '\u004F'
    '\u0050'
    '\u0051'
    '\u0052'
    '\u0053'
    '\u0054'
    '\u0055'
    '\u0056'
    '\u0057'
    '\u0058'
    '\u0059'
    '\u005A'
    '\u005B'
    '\ufffe'
    '\u005D'
    '\ufffe'
    '\u005F'
    '\ufffe'
    '\u0061'
    '\u0062'
    '\u0063'
    '\u0064'
    '\u0065'
    '\u0066'
    '\u0067'
    '\u0068'
    '\u0069'
    '\u006A'
    '\u006B'
    '\u006C'
    '\u006D'
    '\u006E'
    '\u006F'
    '\u0070'
    '\u0071'
    '\u0072'
    '\u0073'
    '\u0074'
    '\u0075'
    '\u0076'
    '\u0077'
    '\u0078'
    '\u0079'
    '\u007A'
    '\ufffe'
    '\u007C'
    '\ufffe'
    '\ufffe'
    '\u007F'
    '\u0080'
    '\u0081'
    '\u0082'
    '\u0083'
    '\u0084'
    '\u0085'
    '\u0086'
    '\u0087'
    '\u0088'
    '\u0089'
    '\u008A'
    '\u008B'
    '\u008C'
    '\u008D'
    '\u008E'
    '\u008F'
    '\u0090'
    '\u0091'
    '\u0092'
    '\u0093'
    '\u0094'
    '\u0095'
    '\u0096'
    '\u0097'
    '\u0098'
    '\u0099'
    '\u009A'
    '\u009B'
    '\u009C'
    '\u009D'
    '\u009E'
    '\u009F'
    '\u00A0'
    '\u00A1'
    '\u00A2'
    '\u00A3'
    '\u0024'
    '\u00A5'
    '\u0023'
    '\u00A7'
    '\u00A4'
    '\ufffe'
    '\ufffe'
    '\u00AB'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\u00B0'
    '\u00B1'
    '\u00B2'
    '\u00B3'
    '\u00D7'
    '\u00B5'
    '\u00B6'
    '\u00B7'
    '\u00F7'
    '\ufffe'
    '\ufffe'
    '\u00BB'
    '\u00BC'
    '\u00BD'
    '\u00BE'
    '\u00BF'
    '\ufffe'
    '\u0300'
    '\u0301'
    '\u0302'
    '\u0303'
    '\u0304'
    '\u0306'
    '\u0307'
    '\u0308'
    '\ufffe'
    '\u030A'
    '\u0327'
    '\u0332'
    '\u030B'
    '\u0328'
    '\u030C'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\ufffe'
    '\u2126'
    '\u00C6'
    '\u00D0'
    '\u00AA'
    '\u0126'
    '\ufffe'
    '\u0132'
    '\u013F'
    '\u0141'
    '\u00D8'
    '\u0152'
    '\u00BA'
    '\u00DE'
    '\u0166'
    '\u014A'
    '\u0149'
    '\u0138'
    '\u00E6'
    '\u0111'
    '\u00F0'
    '\u0127'
    '\u0131'
    '\u0133'
    '\u0140'
    '\u0142'
    '\u00F8'
    '\u0153'
    '\u00DF'
    '\u00FE'
    '\u0167'
    '\u014B'
    '\ufffe'
)
ENCODING_TABLE = codecs.charmap_build(DECODING_TABLE)
