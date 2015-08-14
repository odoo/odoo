# -*- coding: utf-8 -*-

""" ESC/POS Commands (Constants) """

# Feed control sequences
CTL_LF    = '\x0a'             # Print and line feed
CTL_FF    = '\x0c'             # Form feed
CTL_CR    = '\x0d'             # Carriage return
CTL_HT    = '\x09'             # Horizontal tab
CTL_VT    = '\x0b'             # Vertical tab

# RT Status commands
DLE_EOT_PRINTER   = '\x10\x04\x01'  # Transmit printer status
DLE_EOT_OFFLINE   = '\x10\x04\x02'
DLE_EOT_ERROR     = '\x10\x04\x03'
DLE_EOT_PAPER     = '\x10\x04\x04'

# Printer hardware
HW_INIT   = '\x1b\x40'         # Clear data in buffer and reset modes
HW_SELECT = '\x1b\x3d\x01'     # Printer select
HW_RESET  = '\x1b\x3f\x0a\x00' # Reset printer hardware
# Cash Drawer
CD_KICK_2 = '\x1b\x70\x00'     # Sends a pulse to pin 2 [] 
CD_KICK_5 = '\x1b\x70\x01'     # Sends a pulse to pin 5 [] 
# Paper
PAPER_FULL_CUT  = '\x1d\x56\x00' # Full cut paper
PAPER_PART_CUT  = '\x1d\x56\x01' # Partial cut paper
# Text format   
TXT_NORMAL      = '\x1b\x21\x00' # Normal text
TXT_2HEIGHT     = '\x1b\x21\x10' # Double height text
TXT_2WIDTH      = '\x1b\x21\x20' # Double width text
TXT_DOUBLE      = '\x1b\x21\x30' # Double height & Width
TXT_UNDERL_OFF  = '\x1b\x2d\x00' # Underline font OFF
TXT_UNDERL_ON   = '\x1b\x2d\x01' # Underline font 1-dot ON
TXT_UNDERL2_ON  = '\x1b\x2d\x02' # Underline font 2-dot ON
TXT_BOLD_OFF    = '\x1b\x45\x00' # Bold font OFF
TXT_BOLD_ON     = '\x1b\x45\x01' # Bold font ON
TXT_FONT_A      = '\x1b\x4d\x00' # Font type A
TXT_FONT_B      = '\x1b\x4d\x01' # Font type B
TXT_ALIGN_LT    = '\x1b\x61\x00' # Left justification
TXT_ALIGN_CT    = '\x1b\x61\x01' # Centering
TXT_ALIGN_RT    = '\x1b\x61\x02' # Right justification
TXT_COLOR_BLACK = '\x1b\x72\x00' # Default Color
TXT_COLOR_RED   = '\x1b\x72\x01' # Alternative Color ( Usually Red )

# Text Encoding

TXT_ENC_PC437   = '\x1b\x74\x00' # PC437 USA
TXT_ENC_KATAKANA= '\x1b\x74\x01' # KATAKANA (JAPAN)
TXT_ENC_PC850   = '\x1b\x74\x02' # PC850 Multilingual
TXT_ENC_PC860   = '\x1b\x74\x03' # PC860 Portuguese
TXT_ENC_PC863   = '\x1b\x74\x04' # PC863 Canadian-French
TXT_ENC_PC865   = '\x1b\x74\x05' # PC865 Nordic
TXT_ENC_KANJI6  = '\x1b\x74\x06' # One-pass Kanji, Hiragana
TXT_ENC_KANJI7  = '\x1b\x74\x07' # One-pass Kanji 
TXT_ENC_KANJI8  = '\x1b\x74\x08' # One-pass Kanji
TXT_ENC_PC851   = '\x1b\x74\x0b' # PC851 Greek
TXT_ENC_PC853   = '\x1b\x74\x0c' # PC853 Turkish
TXT_ENC_PC857   = '\x1b\x74\x0d' # PC857 Turkish 
TXT_ENC_PC737   = '\x1b\x74\x0e' # PC737 Greek
TXT_ENC_8859_7  = '\x1b\x74\x0f' # ISO8859-7 Greek
TXT_ENC_WPC1252 = '\x1b\x74\x10' # WPC1252
TXT_ENC_PC866   = '\x1b\x74\x11' # PC866 Cyrillic #2
TXT_ENC_PC852   = '\x1b\x74\x12' # PC852 Latin2
TXT_ENC_PC858   = '\x1b\x74\x13' # PC858 Euro
TXT_ENC_KU42    = '\x1b\x74\x14' # KU42 Thai
TXT_ENC_TIS11   = '\x1b\x74\x15' # TIS11 Thai
TXT_ENC_TIS18   = '\x1b\x74\x1a' # TIS18 Thai
TXT_ENC_TCVN3   = '\x1b\x74\x1e' # TCVN3 Vietnamese
TXT_ENC_TCVN3B  = '\x1b\x74\x1f' # TCVN3 Vietnamese
TXT_ENC_PC720   = '\x1b\x74\x20' # PC720 Arabic
TXT_ENC_WPC775  = '\x1b\x74\x21' # WPC775 Baltic Rim
TXT_ENC_PC855   = '\x1b\x74\x22' # PC855 Cyrillic 
TXT_ENC_PC861   = '\x1b\x74\x23' # PC861 Icelandic
TXT_ENC_PC862   = '\x1b\x74\x24' # PC862 Hebrew
TXT_ENC_PC864   = '\x1b\x74\x25' # PC864 Arabic
TXT_ENC_PC869   = '\x1b\x74\x26' # PC869 Greek
TXT_ENC_PC936   = '\x1C\x21\x00' # PC936 GBK(Guobiao Kuozhan)
TXT_ENC_8859_2  = '\x1b\x74\x27' # ISO8859-2 Latin2
TXT_ENC_8859_9  = '\x1b\x74\x28' # ISO8859-2 Latin9
TXT_ENC_PC1098  = '\x1b\x74\x29' # PC1098 Farsi
TXT_ENC_PC1118  = '\x1b\x74\x2a' # PC1118 Lithuanian
TXT_ENC_PC1119  = '\x1b\x74\x2b' # PC1119 Lithuanian
TXT_ENC_PC1125  = '\x1b\x74\x2c' # PC1125 Ukrainian
TXT_ENC_WPC1250 = '\x1b\x74\x2d' # WPC1250 Latin2
TXT_ENC_WPC1251 = '\x1b\x74\x2e' # WPC1251 Cyrillic
TXT_ENC_WPC1253 = '\x1b\x74\x2f' # WPC1253 Greek
TXT_ENC_WPC1254 = '\x1b\x74\x30' # WPC1254 Turkish
TXT_ENC_WPC1255 = '\x1b\x74\x31' # WPC1255 Hebrew
TXT_ENC_WPC1256 = '\x1b\x74\x32' # WPC1256 Arabic
TXT_ENC_WPC1257 = '\x1b\x74\x33' # WPC1257 Baltic Rim
TXT_ENC_WPC1258 = '\x1b\x74\x34' # WPC1258 Vietnamese
TXT_ENC_KZ1048  = '\x1b\x74\x35' # KZ-1048 Kazakhstan

TXT_ENC_KATAKANA_MAP = {
  # Maps UTF-8 Katakana symbols to KATAKANA Page Codes

  # Half-Width Katakanas
  '\xef\xbd\xa1':'\xa1',  # ｡
  '\xef\xbd\xa2':'\xa2',  # ｢
  '\xef\xbd\xa3':'\xa3',  # ｣
  '\xef\xbd\xa4':'\xa4',  # ､
  '\xef\xbd\xa5':'\xa5',  # ･

  '\xef\xbd\xa6':'\xa6',  # ｦ
  '\xef\xbd\xa7':'\xa7',  # ｧ
  '\xef\xbd\xa8':'\xa8',  # ｨ
  '\xef\xbd\xa9':'\xa9',  # ｩ
  '\xef\xbd\xaa':'\xaa',  # ｪ
  '\xef\xbd\xab':'\xab',  # ｫ
  '\xef\xbd\xac':'\xac',  # ｬ
  '\xef\xbd\xad':'\xad',  # ｭ
  '\xef\xbd\xae':'\xae',  # ｮ
  '\xef\xbd\xaf':'\xaf',  # ｯ
  '\xef\xbd\xb0':'\xb0',  # ｰ
  '\xef\xbd\xb1':'\xb1',  # ｱ
  '\xef\xbd\xb2':'\xb2',  # ｲ
  '\xef\xbd\xb3':'\xb3',  # ｳ
  '\xef\xbd\xb4':'\xb4',  # ｴ
  '\xef\xbd\xb5':'\xb5',  # ｵ
  '\xef\xbd\xb6':'\xb6',  # ｶ
  '\xef\xbd\xb7':'\xb7',  # ｷ
  '\xef\xbd\xb8':'\xb8',  # ｸ
  '\xef\xbd\xb9':'\xb9',  # ｹ
  '\xef\xbd\xba':'\xba',  # ｺ
  '\xef\xbd\xbb':'\xbb',  # ｻ
  '\xef\xbd\xbc':'\xbc',  # ｼ
  '\xef\xbd\xbd':'\xbd',  # ｽ
  '\xef\xbd\xbe':'\xbe',  # ｾ
  '\xef\xbd\xbf':'\xbf',  # ｿ
  '\xef\xbe\x80':'\xc0',  # ﾀ
  '\xef\xbe\x81':'\xc1',  # ﾁ
  '\xef\xbe\x82':'\xc2',  # ﾂ
  '\xef\xbe\x83':'\xc3',  # ﾃ
  '\xef\xbe\x84':'\xc4',  # ﾄ
  '\xef\xbe\x85':'\xc5',  # ﾅ
  '\xef\xbe\x86':'\xc6',  # ﾆ
  '\xef\xbe\x87':'\xc7',  # ﾇ
  '\xef\xbe\x88':'\xc8',  # ﾈ
  '\xef\xbe\x89':'\xc9',  # ﾉ
  '\xef\xbe\x8a':'\xca',  # ﾊ
  '\xef\xbe\x8b':'\xcb',  # ﾋ
  '\xef\xbe\x8c':'\xcc',  # ﾌ
  '\xef\xbe\x8d':'\xcd',  # ﾍ
  '\xef\xbe\x8e':'\xce',  # ﾎ
  '\xef\xbe\x8f':'\xcf',  # ﾏ
  '\xef\xbe\x90':'\xd0',  # ﾐ
  '\xef\xbe\x91':'\xd1',  # ﾑ
  '\xef\xbe\x92':'\xd2',  # ﾒ
  '\xef\xbe\x93':'\xd3',  # ﾓ
  '\xef\xbe\x94':'\xd4',  # ﾔ
  '\xef\xbe\x95':'\xd5',  # ﾕ
  '\xef\xbe\x96':'\xd6',  # ﾖ
  '\xef\xbe\x97':'\xd7',  # ﾗ
  '\xef\xbe\x98':'\xd8',  # ﾘ
  '\xef\xbe\x99':'\xd9',  # ﾙ
  '\xef\xbe\x9a':'\xda',  # ﾚ
  '\xef\xbe\x9b':'\xdb',  # ﾛ
  '\xef\xbe\x9c':'\xdc',  # ﾜ
  '\xef\xbe\x9d':'\xdd',  # ﾝ

  '\xef\xbe\x9e':'\xde',  # ﾞ
  '\xef\xbe\x9f':'\xdf',  # ﾟ
}

# Barcod format
BARCODE_TXT_OFF = '\x1d\x48\x00' # HRI barcode chars OFF
BARCODE_TXT_ABV = '\x1d\x48\x01' # HRI barcode chars above
BARCODE_TXT_BLW = '\x1d\x48\x02' # HRI barcode chars below
BARCODE_TXT_BTH = '\x1d\x48\x03' # HRI barcode chars both above and below
BARCODE_FONT_A  = '\x1d\x66\x00' # Font type A for HRI barcode chars
BARCODE_FONT_B  = '\x1d\x66\x01' # Font type B for HRI barcode chars
BARCODE_HEIGHT  = '\x1d\x68\x64' # Barcode Height [1-255]
BARCODE_WIDTH   = '\x1d\x77\x03' # Barcode Width  [2-6]
BARCODE_UPC_A   = '\x1d\x6b\x00' # Barcode type UPC-A
BARCODE_UPC_E   = '\x1d\x6b\x01' # Barcode type UPC-E
BARCODE_EAN13   = '\x1d\x6b\x02' # Barcode type EAN13
BARCODE_EAN8    = '\x1d\x6b\x03' # Barcode type EAN8
BARCODE_CODE39  = '\x1d\x6b\x04' # Barcode type CODE39
BARCODE_ITF     = '\x1d\x6b\x05' # Barcode type ITF
BARCODE_NW7     = '\x1d\x6b\x06' # Barcode type NW7
# Image format  
S_RASTER_N      = '\x1d\x76\x30\x00' # Set raster image normal size
S_RASTER_2W     = '\x1d\x76\x30\x01' # Set raster image double width
S_RASTER_2H     = '\x1d\x76\x30\x02' # Set raster image double height
S_RASTER_Q      = '\x1d\x76\x30\x03' # Set raster image quadruple
