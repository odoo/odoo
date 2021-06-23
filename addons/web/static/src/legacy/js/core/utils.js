odoo.define('web.utils', function (require) {
"use strict";

/**
 * Utils
 *
 * Various generic utility functions
 */

var translation = require('web.translation');

const { Component } = owl;

var _t = translation._t;
var id = -1;

var diacriticsMap = {
'\u0041': 'A','\u24B6': 'A','\uFF21': 'A','\u00C0': 'A','\u00C1': 'A','\u00C2': 'A','\u1EA6': 'A','\u1EA4': 'A','\u1EAA': 'A','\u1EA8': 'A',
'\u00C3': 'A','\u0100': 'A','\u0102': 'A','\u1EB0': 'A','\u1EAE': 'A','\u1EB4': 'A','\u1EB2': 'A','\u0226': 'A','\u01E0': 'A','\u00C4': 'A',
'\u01DE': 'A','\u1EA2': 'A','\u00C5': 'A','\u01FA': 'A','\u01CD': 'A','\u0200': 'A','\u0202': 'A','\u1EA0': 'A','\u1EAC': 'A','\u1EB6': 'A',
'\u1E00': 'A','\u0104': 'A','\u023A': 'A','\u2C6F': 'A',

'\uA732': 'AA',
'\u00C6': 'AE','\u01FC': 'AE','\u01E2': 'AE',
'\uA734': 'AO',
'\uA736': 'AU',
'\uA738': 'AV','\uA73A': 'AV',
'\uA73C': 'AY',
'\u0042': 'B','\u24B7': 'B','\uFF22': 'B','\u1E02': 'B','\u1E04': 'B','\u1E06': 'B','\u0243': 'B','\u0182': 'B','\u0181': 'B',

'\u0043': 'C','\u24B8': 'C','\uFF23': 'C','\u0106': 'C','\u0108': 'C','\u010A': 'C','\u010C': 'C','\u00C7': 'C','\u1E08': 'C','\u0187': 'C',
'\u023B': 'C','\uA73E': 'C',

'\u0044': 'D','\u24B9': 'D','\uFF24': 'D','\u1E0A': 'D','\u010E': 'D','\u1E0C': 'D','\u1E10': 'D','\u1E12': 'D','\u1E0E': 'D','\u0110': 'D',
'\u018B': 'D','\u018A': 'D','\u0189': 'D','\uA779': 'D',

'\u01F1': 'DZ','\u01C4': 'DZ',
'\u01F2': 'Dz','\u01C5': 'Dz',

'\u0045': 'E','\u24BA': 'E','\uFF25': 'E','\u00C8': 'E','\u00C9': 'E','\u00CA': 'E','\u1EC0': 'E','\u1EBE': 'E','\u1EC4': 'E','\u1EC2': 'E',
'\u1EBC': 'E','\u0112': 'E','\u1E14': 'E','\u1E16': 'E','\u0114': 'E','\u0116': 'E','\u00CB': 'E','\u1EBA': 'E','\u011A': 'E','\u0204': 'E',
'\u0206': 'E','\u1EB8': 'E','\u1EC6': 'E','\u0228': 'E','\u1E1C': 'E','\u0118': 'E','\u1E18': 'E','\u1E1A': 'E','\u0190': 'E','\u018E': 'E',

'\u0046': 'F','\u24BB': 'F','\uFF26': 'F','\u1E1E': 'F','\u0191': 'F','\uA77B': 'F',

'\u0047': 'G','\u24BC': 'G','\uFF27': 'G','\u01F4': 'G','\u011C': 'G','\u1E20': 'G','\u011E': 'G','\u0120': 'G','\u01E6': 'G','\u0122': 'G',
'\u01E4': 'G','\u0193': 'G','\uA7A0': 'G','\uA77D': 'G','\uA77E': 'G',

'\u0048': 'H','\u24BD': 'H','\uFF28': 'H','\u0124': 'H','\u1E22': 'H','\u1E26': 'H','\u021E': 'H','\u1E24': 'H','\u1E28': 'H','\u1E2A': 'H',
'\u0126': 'H','\u2C67': 'H','\u2C75': 'H','\uA78D': 'H',

'\u0049': 'I','\u24BE': 'I','\uFF29': 'I','\u00CC': 'I','\u00CD': 'I','\u00CE': 'I','\u0128': 'I','\u012A': 'I','\u012C': 'I','\u0130': 'I',
'\u00CF': 'I','\u1E2E': 'I','\u1EC8': 'I','\u01CF': 'I','\u0208': 'I','\u020A': 'I','\u1ECA': 'I','\u012E': 'I','\u1E2C': 'I','\u0197': 'I',

'\u004A': 'J','\u24BF': 'J','\uFF2A': 'J','\u0134': 'J','\u0248': 'J',

'\u004B': 'K','\u24C0': 'K','\uFF2B': 'K','\u1E30': 'K','\u01E8': 'K','\u1E32': 'K','\u0136': 'K','\u1E34': 'K','\u0198': 'K','\u2C69': 'K',
'\uA740': 'K','\uA742': 'K','\uA744': 'K','\uA7A2': 'K',

'\u004C': 'L','\u24C1': 'L','\uFF2C': 'L','\u013F': 'L','\u0139': 'L','\u013D': 'L','\u1E36': 'L','\u1E38': 'L','\u013B': 'L','\u1E3C': 'L',
'\u1E3A': 'L','\u0141': 'L','\u023D': 'L','\u2C62': 'L','\u2C60': 'L','\uA748': 'L','\uA746': 'L','\uA780': 'L',

'\u01C7': 'LJ',
'\u01C8': 'Lj',
'\u004D': 'M','\u24C2': 'M','\uFF2D': 'M','\u1E3E': 'M','\u1E40': 'M','\u1E42': 'M','\u2C6E': 'M','\u019C': 'M',

'\u004E': 'N','\u24C3': 'N','\uFF2E': 'N','\u01F8': 'N','\u0143': 'N','\u00D1': 'N','\u1E44': 'N','\u0147': 'N','\u1E46': 'N','\u0145': 'N',
'\u1E4A': 'N','\u1E48': 'N','\u0220': 'N','\u019D': 'N','\uA790': 'N','\uA7A4': 'N',

'\u01CA': 'NJ',
'\u01CB': 'Nj',

'\u004F': 'O','\u24C4': 'O','\uFF2F': 'O','\u00D2': 'O','\u00D3': 'O','\u00D4': 'O','\u1ED2': 'O','\u1ED0': 'O','\u1ED6': 'O','\u1ED4': 'O',
'\u00D5': 'O','\u1E4C': 'O','\u022C': 'O','\u1E4E': 'O','\u014C': 'O','\u1E50': 'O','\u1E52': 'O','\u014E': 'O','\u022E': 'O','\u0230': 'O',
'\u00D6': 'O','\u022A': 'O','\u1ECE': 'O','\u0150': 'O','\u01D1': 'O','\u020C': 'O','\u020E': 'O','\u01A0': 'O','\u1EDC': 'O','\u1EDA': 'O',
'\u1EE0': 'O','\u1EDE': 'O','\u1EE2': 'O','\u1ECC': 'O','\u1ED8': 'O','\u01EA': 'O','\u01EC': 'O','\u00D8': 'O','\u01FE': 'O','\u0186': 'O',
'\u019F': 'O','\uA74A': 'O','\uA74C': 'O',

'\u01A2': 'OI',
'\uA74E': 'OO',
'\u0222': 'OU',
'\u0050': 'P','\u24C5': 'P','\uFF30': 'P','\u1E54': 'P','\u1E56': 'P','\u01A4': 'P','\u2C63': 'P','\uA750': 'P','\uA752': 'P','\uA754': 'P',
'\u0051': 'Q','\u24C6': 'Q','\uFF31': 'Q','\uA756': 'Q','\uA758': 'Q','\u024A': 'Q',

'\u0052': 'R','\u24C7': 'R','\uFF32': 'R','\u0154': 'R','\u1E58': 'R','\u0158': 'R','\u0210': 'R','\u0212': 'R','\u1E5A': 'R','\u1E5C': 'R',
'\u0156': 'R','\u1E5E': 'R','\u024C': 'R','\u2C64': 'R','\uA75A': 'R','\uA7A6': 'R','\uA782': 'R',

'\u0053': 'S','\u24C8': 'S','\uFF33': 'S','\u1E9E': 'S','\u015A': 'S','\u1E64': 'S','\u015C': 'S','\u1E60': 'S','\u0160': 'S','\u1E66': 'S',
'\u1E62': 'S','\u1E68': 'S','\u0218': 'S','\u015E': 'S','\u2C7E': 'S','\uA7A8': 'S','\uA784': 'S',

'\u0054': 'T','\u24C9': 'T','\uFF34': 'T','\u1E6A': 'T','\u0164': 'T','\u1E6C': 'T','\u021A': 'T','\u0162': 'T','\u1E70': 'T','\u1E6E': 'T',
'\u0166': 'T','\u01AC': 'T','\u01AE': 'T','\u023E': 'T','\uA786': 'T',

'\uA728': 'TZ',

'\u0055': 'U','\u24CA': 'U','\uFF35': 'U','\u00D9': 'U','\u00DA': 'U','\u00DB': 'U','\u0168': 'U','\u1E78': 'U','\u016A': 'U','\u1E7A': 'U',
'\u016C': 'U','\u00DC': 'U','\u01DB': 'U','\u01D7': 'U','\u01D5': 'U','\u01D9': 'U','\u1EE6': 'U','\u016E': 'U','\u0170': 'U','\u01D3': 'U',
'\u0214': 'U','\u0216': 'U','\u01AF': 'U','\u1EEA': 'U','\u1EE8': 'U','\u1EEE': 'U','\u1EEC': 'U','\u1EF0': 'U','\u1EE4': 'U','\u1E72': 'U',
'\u0172': 'U','\u1E76': 'U','\u1E74': 'U','\u0244': 'U',

'\u0056': 'V','\u24CB': 'V','\uFF36': 'V','\u1E7C': 'V','\u1E7E': 'V','\u01B2': 'V','\uA75E': 'V','\u0245': 'V',
'\uA760': 'VY',
'\u0057': 'W','\u24CC': 'W','\uFF37': 'W','\u1E80': 'W','\u1E82': 'W','\u0174': 'W','\u1E86': 'W','\u1E84': 'W','\u1E88': 'W','\u2C72': 'W',
'\u0058': 'X','\u24CD': 'X','\uFF38': 'X','\u1E8A': 'X','\u1E8C': 'X',

'\u0059': 'Y','\u24CE': 'Y','\uFF39': 'Y','\u1EF2': 'Y','\u00DD': 'Y','\u0176': 'Y','\u1EF8': 'Y','\u0232': 'Y','\u1E8E': 'Y','\u0178': 'Y',
'\u1EF6': 'Y','\u1EF4': 'Y','\u01B3': 'Y','\u024E': 'Y','\u1EFE': 'Y',

'\u005A': 'Z','\u24CF': 'Z','\uFF3A': 'Z','\u0179': 'Z','\u1E90': 'Z','\u017B': 'Z','\u017D': 'Z','\u1E92': 'Z','\u1E94': 'Z','\u01B5': 'Z',
'\u0224': 'Z','\u2C7F': 'Z','\u2C6B': 'Z','\uA762': 'Z',

'\u0061': 'a','\u24D0': 'a','\uFF41': 'a','\u1E9A': 'a','\u00E0': 'a','\u00E1': 'a','\u00E2': 'a','\u1EA7': 'a','\u1EA5': 'a','\u1EAB': 'a',
'\u1EA9': 'a','\u00E3': 'a','\u0101': 'a','\u0103': 'a','\u1EB1': 'a','\u1EAF': 'a','\u1EB5': 'a','\u1EB3': 'a','\u0227': 'a','\u01E1': 'a',
'\u00E4': 'a','\u01DF': 'a','\u1EA3': 'a','\u00E5': 'a','\u01FB': 'a','\u01CE': 'a','\u0201': 'a','\u0203': 'a','\u1EA1': 'a','\u1EAD': 'a',
'\u1EB7': 'a','\u1E01': 'a','\u0105': 'a','\u2C65': 'a','\u0250': 'a',

'\uA733': 'aa',
'\u00E6': 'ae','\u01FD': 'ae','\u01E3': 'ae',
'\uA735': 'ao',
'\uA737': 'au',
'\uA739': 'av','\uA73B': 'av',
'\uA73D': 'ay',
'\u0062': 'b','\u24D1': 'b','\uFF42': 'b','\u1E03': 'b','\u1E05': 'b','\u1E07': 'b','\u0180': 'b','\u0183': 'b','\u0253': 'b',

'\u0063': 'c','\u24D2': 'c','\uFF43': 'c','\u0107': 'c','\u0109': 'c','\u010B': 'c','\u010D': 'c','\u00E7': 'c','\u1E09': 'c','\u0188': 'c',
'\u023C': 'c','\uA73F': 'c','\u2184': 'c',

'\u0064': 'd','\u24D3': 'd','\uFF44': 'd','\u1E0B': 'd','\u010F': 'd','\u1E0D': 'd','\u1E11': 'd','\u1E13': 'd','\u1E0F': 'd','\u0111': 'd',
'\u018C': 'd','\u0256': 'd','\u0257': 'd','\uA77A': 'd',

'\u01F3': 'dz','\u01C6': 'dz',

'\u0065': 'e','\u24D4': 'e','\uFF45': 'e','\u00E8': 'e','\u00E9': 'e','\u00EA': 'e','\u1EC1': 'e','\u1EBF': 'e','\u1EC5': 'e','\u1EC3': 'e',
'\u1EBD': 'e','\u0113': 'e','\u1E15': 'e','\u1E17': 'e','\u0115': 'e','\u0117': 'e','\u00EB': 'e','\u1EBB': 'e','\u011B': 'e','\u0205': 'e',
'\u0207': 'e','\u1EB9': 'e','\u1EC7': 'e','\u0229': 'e','\u1E1D': 'e','\u0119': 'e','\u1E19': 'e','\u1E1B': 'e','\u0247': 'e','\u025B': 'e',
'\u01DD': 'e',

'\u0066': 'f','\u24D5': 'f','\uFF46': 'f','\u1E1F': 'f','\u0192': 'f','\uA77C': 'f',

'\u0067': 'g','\u24D6': 'g','\uFF47': 'g','\u01F5': 'g','\u011D': 'g','\u1E21': 'g','\u011F': 'g','\u0121': 'g','\u01E7': 'g','\u0123': 'g',
'\u01E5': 'g','\u0260': 'g','\uA7A1': 'g','\u1D79': 'g','\uA77F': 'g',

'\u0068': 'h','\u24D7': 'h','\uFF48': 'h','\u0125': 'h','\u1E23': 'h','\u1E27': 'h','\u021F': 'h','\u1E25': 'h','\u1E29': 'h','\u1E2B': 'h',
'\u1E96': 'h','\u0127': 'h','\u2C68': 'h','\u2C76': 'h','\u0265': 'h',

'\u0195': 'hv',

'\u0069': 'i','\u24D8': 'i','\uFF49': 'i','\u00EC': 'i','\u00ED': 'i','\u00EE': 'i','\u0129': 'i','\u012B': 'i','\u012D': 'i','\u00EF': 'i',
'\u1E2F': 'i','\u1EC9': 'i','\u01D0': 'i','\u0209': 'i','\u020B': 'i','\u1ECB': 'i','\u012F': 'i','\u1E2D': 'i','\u0268': 'i','\u0131': 'i',

'\u006A': 'j','\u24D9': 'j','\uFF4A': 'j','\u0135': 'j','\u01F0': 'j','\u0249': 'j',

'\u006B': 'k','\u24DA': 'k','\uFF4B': 'k','\u1E31': 'k','\u01E9': 'k','\u1E33': 'k','\u0137': 'k','\u1E35': 'k','\u0199': 'k','\u2C6A': 'k',
'\uA741': 'k','\uA743': 'k','\uA745': 'k','\uA7A3': 'k',

'\u006C': 'l','\u24DB': 'l','\uFF4C': 'l','\u0140': 'l','\u013A': 'l','\u013E': 'l','\u1E37': 'l','\u1E39': 'l','\u013C': 'l','\u1E3D': 'l',
'\u1E3B': 'l','\u017F': 'l','\u0142': 'l','\u019A': 'l','\u026B': 'l','\u2C61': 'l','\uA749': 'l','\uA781': 'l','\uA747': 'l',

'\u01C9': 'lj',
'\u006D': 'm','\u24DC': 'm','\uFF4D': 'm','\u1E3F': 'm','\u1E41': 'm','\u1E43': 'm','\u0271': 'm','\u026F': 'm',

'\u006E': 'n','\u24DD': 'n','\uFF4E': 'n','\u01F9': 'n','\u0144': 'n','\u00F1': 'n','\u1E45': 'n','\u0148': 'n','\u1E47': 'n','\u0146': 'n',
'\u1E4B': 'n','\u1E49': 'n','\u019E': 'n','\u0272': 'n','\u0149': 'n','\uA791': 'n','\uA7A5': 'n',

'\u01CC': 'nj',

'\u006F': 'o','\u24DE': 'o','\uFF4F': 'o','\u00F2': 'o','\u00F3': 'o','\u00F4': 'o','\u1ED3': 'o','\u1ED1': 'o','\u1ED7': 'o','\u1ED5': 'o',
'\u00F5': 'o','\u1E4D': 'o','\u022D': 'o','\u1E4F': 'o','\u014D': 'o','\u1E51': 'o','\u1E53': 'o','\u014F': 'o','\u022F': 'o','\u0231': 'o',
'\u00F6': 'o','\u022B': 'o','\u1ECF': 'o','\u0151': 'o','\u01D2': 'o','\u020D': 'o','\u020F': 'o','\u01A1': 'o','\u1EDD': 'o','\u1EDB': 'o',
'\u1EE1': 'o','\u1EDF': 'o','\u1EE3': 'o','\u1ECD': 'o','\u1ED9': 'o','\u01EB': 'o','\u01ED': 'o','\u00F8': 'o','\u01FF': 'o','\u0254': 'o',
'\uA74B': 'o','\uA74D': 'o','\u0275': 'o',

'\u01A3': 'oi',
'\u0223': 'ou',
'\uA74F': 'oo',
'\u0070': 'p','\u24DF': 'p','\uFF50': 'p','\u1E55': 'p','\u1E57': 'p','\u01A5': 'p','\u1D7D': 'p','\uA751': 'p','\uA753': 'p','\uA755': 'p',
'\u0071': 'q','\u24E0': 'q','\uFF51': 'q','\u024B': 'q','\uA757': 'q','\uA759': 'q',

'\u0072': 'r','\u24E1': 'r','\uFF52': 'r','\u0155': 'r','\u1E59': 'r','\u0159': 'r','\u0211': 'r','\u0213': 'r','\u1E5B': 'r','\u1E5D': 'r',
'\u0157': 'r','\u1E5F': 'r','\u024D': 'r','\u027D': 'r','\uA75B': 'r','\uA7A7': 'r','\uA783': 'r',

'\u0073': 's','\u24E2': 's','\uFF53': 's','\u00DF': 's','\u015B': 's','\u1E65': 's','\u015D': 's','\u1E61': 's','\u0161': 's','\u1E67': 's',
'\u1E63': 's','\u1E69': 's','\u0219': 's','\u015F': 's','\u023F': 's','\uA7A9': 's','\uA785': 's','\u1E9B': 's',

'\u0074': 't','\u24E3': 't','\uFF54': 't','\u1E6B': 't','\u1E97': 't','\u0165': 't','\u1E6D': 't','\u021B': 't','\u0163': 't','\u1E71': 't',
'\u1E6F': 't','\u0167': 't','\u01AD': 't','\u0288': 't','\u2C66': 't','\uA787': 't',

'\uA729': 'tz',

'\u0075': 'u','\u24E4': 'u','\uFF55': 'u','\u00F9': 'u','\u00FA': 'u','\u00FB': 'u','\u0169': 'u','\u1E79': 'u','\u016B': 'u','\u1E7B': 'u',
'\u016D': 'u','\u00FC': 'u','\u01DC': 'u','\u01D8': 'u','\u01D6': 'u','\u01DA': 'u','\u1EE7': 'u','\u016F': 'u','\u0171': 'u','\u01D4': 'u',
'\u0215': 'u','\u0217': 'u','\u01B0': 'u','\u1EEB': 'u','\u1EE9': 'u','\u1EEF': 'u','\u1EED': 'u','\u1EF1': 'u','\u1EE5': 'u','\u1E73': 'u',
'\u0173': 'u','\u1E77': 'u','\u1E75': 'u','\u0289': 'u',

'\u0076': 'v','\u24E5': 'v','\uFF56': 'v','\u1E7D': 'v','\u1E7F': 'v','\u028B': 'v','\uA75F': 'v','\u028C': 'v',
'\uA761': 'vy',
'\u0077': 'w','\u24E6': 'w','\uFF57': 'w','\u1E81': 'w','\u1E83': 'w','\u0175': 'w','\u1E87': 'w','\u1E85': 'w','\u1E98': 'w','\u1E89': 'w',
'\u2C73': 'w',
'\u0078': 'x','\u24E7': 'x','\uFF58': 'x','\u1E8B': 'x','\u1E8D': 'x',

'\u0079': 'y','\u24E8': 'y','\uFF59': 'y','\u1EF3': 'y','\u00FD': 'y','\u0177': 'y','\u1EF9': 'y','\u0233': 'y','\u1E8F': 'y','\u00FF': 'y',
'\u1EF7': 'y','\u1E99': 'y','\u1EF5': 'y','\u01B4': 'y','\u024F': 'y','\u1EFF': 'y',

'\u007A': 'z','\u24E9': 'z','\uFF5A': 'z','\u017A': 'z','\u1E91': 'z','\u017C': 'z','\u017E': 'z','\u1E93': 'z','\u1E95': 'z','\u01B6': 'z',
'\u0225': 'z','\u0240': 'z','\u2C6C': 'z','\uA763': 'z',
};

const patchMap = new WeakMap();

/**
 * Helper function returning an extraction handler to use on array elements to
 * return a certain attribute or mutated form of the element.
 *
 * @private
 * @param {string | function} criterion
 * @returns {(element: any) => any}
 */
function _getExtractorFrom(criterion) {
    if (criterion) {
        switch (typeof criterion) {
            case 'string': return element => element[criterion];
            case 'function': return criterion;
            default: throw new Error(
                `Expected criterion of type 'string' or 'function' and got '${typeof criterion}'`
            );
        }
    } else {
        return element => element;
    }
}

class AlreadyDefinedPatchError extends Error {
    constructor() {
        super(...arguments);
        this.name = 'AlreadyDefinedPatchError';
    }
}
class UnknownPatchError extends Error {
    constructor() {
        super(...arguments);
        this.name = 'UnknownPatchError';
    }
}

const __escape = _.escape;
_.escapeMethod = Symbol('html')
_.escape = function escape(s) {
    return s[_.escapeMethod] ? s[_.escapeMethod]() : __escape(s);
}

// notable issues:
// * objects can't be negative in JS, so !!"" -> false but
//   !!(new String) -> true, likewise markup
// TODO (?)
// * Markup.join / Markup#join => escapes items and returns a Markup
// * Markup#replace => automatically escapes the replacements (difficult impl)

// get a reference to the internalMarkup class from owl
const _Markup = owl.markup('').constructor; 
_Markup.prototype[_.escapeMethod] = function () {
    return this;
}

// exposed for qweb2.js
window._Markup = _Markup;

/**
 * Returns a markup object, which acts like a String but is considered safe by
 * `_.escape`, and will therefore be injected as-is (without additional
 * escaping) in templates. Can be used to inject dynamic HTML in templates
 * (where the template itself can't), see first example.
 *
 * Can also be used as a *template tag*, in which case the literal content
 * won't be escaped but the substitutions which are not already markup objects
 * will be.
 *
 * ## WARNINGS:
 * * A markup object is a `String` (boxed) but not a `string` (primitive), they
 *   typecheck differently which can be relevant.
 * * To strip out the "markupness", just call `String(markup)`.
 * * Most string operations (e.g. concatenation, `String#replace`, ...) will
 *   also strip out markupness
 * * If the input is empty, returns a regular string (that way boolean tests
 *   work as expected).
 *
 * @returns a markup object
 *
 * @example regular function
 * let h;
 * if (someTest) {
 *     h = Markup(_t("This is a <strong>success</strong>"));
 * } else {
 *     h = Markup(_t("Things did <strong>not</strong> work out"));
 * }
 * qweb.render("some_template", { message: h });
 *
 * @example template tag
 * const escaped = "<some> text";
 * const asis = Markup`some <b>text</b>`;
 * const h = Markup`Regular strings get ${escaped} but markup is injected ${asis}`;
 */
function Markup(v, ...exprs) {
    if (!(v instanceof Array)) {
        return v ? new _Markup(v) : '';
    }
    const elements = [];
    let i = 0;
    for(; i < exprs.length; ++i) {
        elements.push(v[i], _.escape(exprs[i]));
    }
    elements.push(v[i]);

    const s = elements.join('');
    if (!s) { return '' }
    return new _Markup(s);
}

const utils = {
    AlreadyDefinedPatchError,
    UnknownPatchError,
    Markup,

    /**
     * Throws an error if the given condition is not true
     *
     * @param {any} bool
     */
    assert: function (bool) {
        if (!bool) {
            throw new Error("AssertionError");
        }
    },
    /**
     * Check if the value is a bin_size or not.
     * If not, compute an approximate size out of the base64 encoded string.
     *
     * @param  {string} value original format
     * @return {string} bin_size (human-readable)
     */
    binaryToBinsize: function (value) {
        if (!this.is_bin_size(value)) {
            // Computing approximate size out of base64 encoded string
            // http://en.wikipedia.org/wiki/Base64#MIME
            return this.human_size(value.length / 1.37);
        }
        // already bin_size
        return value;
    },
    /**
     * Confines a value inside an interval
     *
     * @param {number} [val] the value to confine
     * @param {number} [min] the minimum of the interval
     * @param {number} [max] the maximum of the interval
     * @return {number} val if val is in [min, max], min if val < min and max
     *   otherwise
     */
    confine: function (val, min, max) {
        return Math.max(min, Math.min(max, val));
    },
    /**
     * Looks through the list and returns the first value that matches all
     * of the key-value pairs listed in properties.
     * If no match is found, or if list is empty, undefined will be returned.
     *
     * @param {Array} list
     * @param {Object} props
     * @returns {any|undefined} first element in list that matches all props
     */
    findWhere: function (list, props) {
        if (!Array.isArray(list) || !props) {
            return;
        }
        return list.filter((item) => item !== undefined).find((item) => {
            return Object.keys(props).every((key) => {
                return item[key] === props[key];
            })
        });
    },
    /**
     * @param {number} value
     * @param {integer} decimals
     * @returns {boolean}
     */
    float_is_zero: function (value, decimals) {
        var epsilon = Math.pow(10, -decimals);
        return Math.abs(utils.round_precision(value, epsilon)) < epsilon;
    },
    /**
     * Generate a unique numerical ID
     *
     * @returns {integer}
     */
    generateID: function () {
        return ++id;
    },
    /**
     * Gets dataURL (base64 data) from the given file or blob.
     * Technically wraps FileReader.readAsDataURL in Promise.
     *
     * @param {Blob|File} file
     * @returns {Promise} resolved with the dataURL, or rejected if the file is
     *  empty or if an error occurs.
     */
    getDataURLFromFile: function (file) {
        if (!file) {
            return Promise.reject();
        }
        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.addEventListener('load', function () {
                resolve(reader.result);
            });
            reader.addEventListener('abort', reject);
            reader.addEventListener('error', reject);
            reader.readAsDataURL(file);
        });
    },
    /**
     * Returns an object holding different groups defined by a given criterion
     * or a default one. Each group is a subset of the original given list.
     * The given criterion can either be:
     * - a string: a property name on the list elements which value will be the
     * group name,
     * - a function: a handler that will return the group name from a given
     * element.
     *
     * @param {any[]} list
     * @param {string | function} [criterion]
     * @returns {Object}
     */
    groupBy: function (list, criterion) {
        const extract = _getExtractorFrom(criterion);
        const groups = {};
        for (const element of list) {
            const group = String(extract(element));
            if (!(group in groups)) {
                groups[group] = [];
            }
            groups[group].push(element);
        }
        return groups;
    },
    /**
     * Returns a human readable number (e.g. 34000 -> 34k).
     *
     * @param {number} number
     * @param {integer} [decimals=0]
     *        maximum number of decimals to use in human readable representation
     * @param {integer} [minDigits=1]
     *        the minimum number of digits to preserve when switching to another
     *        level of thousands (e.g. with a value of '2', 4321 will still be
     *        represented as 4321 otherwise it will be down to one digit (4k))
     * @param {function} [formatterCallback]
     *        a callback to transform the final number before adding the
     *        thousands symbol (default to adding thousands separators (useful
     *        if minDigits > 1))
     * @returns {string}
     */
    human_number: function (number, decimals, minDigits, formatterCallback) {
        number = Math.round(number);
        decimals = decimals | 0;
        minDigits = minDigits || 1;
        formatterCallback = formatterCallback || utils.insert_thousand_seps;

        var d2 = Math.pow(10, decimals);
        var val = _t('kMGTPE');
        var symbol = '';
        var numberMagnitude = number.toExponential().split('e')[1];
        // the case numberMagnitude >= 21 corresponds to a number
        // better expressed in the scientific format.
        if (numberMagnitude >= 21) {
            // we do not use number.toExponential(decimals) because we want to
            // avoid the possible useless O decimals: 1e.+24 preferred to 1.0e+24
            number = Math.round(number * Math.pow(10, decimals - numberMagnitude)) / d2;
            // formatterCallback seems useless here.
            return number + 'e' + numberMagnitude;
        }
        var sign = Math.sign(number);
        number = Math.abs(number);
        for (var i = val.length; i > 0 ; i--) {
            var s = Math.pow(10, i * 3);
            if (s <= number / Math.pow(10, minDigits - 1)) {
                number = Math.round(number * d2 / s) / d2;
                symbol = val[i - 1];
                break;
            }
        }
        number = sign * number;
        return formatterCallback('' + number) + symbol;
    },
    /**
     * Returns a human readable size
     *
     * @param {Number} size number of bytes
     */
    human_size: function (size) {
        var units = _t("Bytes|Kb|Mb|Gb|Tb|Pb|Eb|Zb|Yb").split('|');
        var i = 0;
        while (size >= 1024) {
            size /= 1024;
            ++i;
        }
        return size.toFixed(2) + ' ' + units[i].trim();
    },
    /**
     * Insert "thousands" separators in the provided number (which is actually
     * a string)
     *
     * @param {String} num
     * @returns {String}
     */
    insert_thousand_seps: function (num) {
        var negative = num[0] === '-';
        num = (negative ? num.slice(1) : num);
        return (negative ? '-' : '') + utils.intersperse(
            num, _t.database.parameters.grouping, _t.database.parameters.thousands_sep);
    },
    /**
     * Intersperses ``separator`` in ``str`` at the positions indicated by
     * ``indices``.
     *
     * ``indices`` is an array of relative offsets (from the previous insertion
     * position, starting from the end of the string) at which to insert
     * ``separator``.
     *
     * There are two special values:
     *
     * ``-1``
     *   indicates the insertion should end now
     * ``0``
     *   indicates that the previous section pattern should be repeated (until all
     *   of ``str`` is consumed)
     *
     * @param {String} str
     * @param {Array<Number>} indices
     * @param {String} separator
     * @returns {String}
     */
    intersperse: function (str, indices, separator) {
        separator = separator || '';
        var result = [], last = str.length;

        for(var i=0; i<indices.length; ++i) {
            var section = indices[i];
            if (section === -1 || last <= 0) {
                // Done with string, or -1 (stops formatting string)
                break;
            } else if(section === 0 && i === 0) {
                // repeats previous section, which there is none => stop
                break;
            } else if (section === 0) {
                // repeat previous section forever
                //noinspection AssignmentToForLoopParameterJS
                section = indices[--i];
            }
            result.push(str.substring(last-section, last));
            last -= section;
        }

        var s = str.substring(0, last);
        if (s) { result.push(s); }
        return result.reverse().join(separator);
    },
    /**
     * @param {any} object
     * @param {any} path
     * @returns
     */
    into: function (object, path) {
        if (!_(path).isArray()) {
            path = path.split('.');
        }
        for (var i = 0; i < path.length; i++) {
            object = object[path[i]];
        }
        return object;
    },
    /**
     * @param {string} v
     * @returns {boolean}
     */
    is_bin_size: function (v) {
        return (/^\d+(\.\d*)? [^0-9]+$/).test(v);
    },
    /**
     * Checks if a class is an extension of Component.
     *
     * @param {any} value A class reference
     */
    isComponent: function (value) {
        return value.prototype instanceof Component;
    },
    /**
     * Checks if a keyboard event concerns
     * the numpad decimal separator key.
     *
     * Some countries may emit a comma instead
     * of a period when this key get pressed.
     * More info: https://www.iso.org/schema/isosts/v1.0/doc/n-cdf0.html
     *
     * @param {KeyboardEvent} ev
     * @returns {boolean}
     */
    isNumpadDecimalSeparatorKey(ev) {
        return ['.', ','].includes(ev.key) && ev.code === 'NumpadDecimal';
    },
    /**
     * Returns whether the given anchor is valid.
     *
     * This test is useful to prevent a crash that would happen if using an invalid
     * anchor as a selector.
     *
     * @param {string} anchor
     * @returns {boolean}
     */
    isValidAnchor: function (anchor) {
        return /^#[\w-]+$/.test(anchor);
    },
    /**
     * @param {any} node
     * @param {any} human_readable
     * @param {any} indent
     * @returns {string}
     */
    json_node_to_xml: function (node, human_readable, indent) {
        // For debugging purpose, this function will convert a json node back to xml
        indent = indent || 0;
        var sindent = (human_readable ? (new Array(indent + 1).join('\t')) : ''),
            r = sindent + '<' + node.tag,
            cr = human_readable ? '\n' : '';

        if (typeof(node) === 'string') {
            return sindent + node.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        } else if (typeof(node.tag) !== 'string' || node.children && !(node.children instanceof Array) || node.attrs && !(node.attrs instanceof Object)) {
            throw new Error(
                _.str.sprintf(_t("Node [%s] is not a JSONified XML node"),
                            JSON.stringify(node)));
        }
        for (var attr in node.attrs) {
            var vattr = node.attrs[attr];
            if (typeof(vattr) !== 'string') {
                // domains, ...
                vattr = JSON.stringify(vattr);
            }
            vattr = vattr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
            if (human_readable) {
                vattr = vattr.replace(/&quot;/g, "'");
            }
            r += ' ' + attr + '="' + vattr + '"';
        }
        if (node.children && node.children.length) {
            r += '>' + cr;
            var childs = [];
            for (var i = 0, ii = node.children.length; i < ii; i++) {
                childs.push(utils.json_node_to_xml(node.children[i], human_readable, indent + 1));
            }
            r += childs.join(cr);
            r += cr + sindent + '</' + node.tag + '>';
            return r;
        } else {
            return r + '/>';
        }
    },
    /**
     * Left-pad provided arg 1 with zeroes until reaching size provided by second
     * argument.
     *
     * @see rpad
     *
     * @param {number|string} str value to pad
     * @param {number} size size to reach on the final padded value
     * @returns {string} padded string
     */
    lpad: function (str, size) {
        str = "" + str;
        return new Array(size - str.length + 1).join('0') + str;
    },
    /**
     * @param {any[]} arr
     * @param {Function} fn
     * @returns {any[]}
     */
    partitionBy(arr, fn) {
        let lastGroup = false;
        let lastValue;
        return arr.reduce((acc, cur) => {
            let curVal = fn(cur);
            if (lastGroup) {
                if (curVal === lastValue) {
                    lastGroup.push(cur);
                } else {
                    lastGroup = false;
                }
            }
            if (!lastGroup) {
                lastGroup = [cur];
                acc.push(lastGroup);
            }
            lastValue = curVal;
            return acc;
        }, []);
    },
    /**
     * Patch an object and return a function that remove the patch
     * when called.
     *
     * @param {Object} obj Object to patch
     * @param {string} patchName
     * @param {Object} patch
     */
    patch: function (obj, patchName, patch) {
        if (!patchMap.has(obj)) {
            patchMap.set(obj, {
                original: {},
                patches: [],
            });
        }
        const objDesc = patchMap.get(obj);
        if (objDesc.patches.some(p => p.name === patchName)) {
            throw new AlreadyDefinedPatchError(`Patch ${patchName} is already defined`);
        }
        objDesc.patches.push({
            name: patchName,
            patch,
        });

        for (const k in patch) {
            let prevDesc = null;
            let proto = obj;
            do {
                prevDesc = Object.getOwnPropertyDescriptor(proto, k);
                proto = Object.getPrototypeOf(proto);
            } while (!prevDesc && proto);

            const newDesc = Object.getOwnPropertyDescriptor(patch, k);
            if (!objDesc.original.hasOwnProperty(k)) {
                objDesc.original[k] = Object.getOwnPropertyDescriptor(obj, k);
            }

            if (prevDesc) {
                const patchedFnName = `${k} (patch ${patchName})`;

                if (prevDesc.value && typeof newDesc.value === "function") {
                    makeIntermediateFunction("value", prevDesc, newDesc, patchedFnName);
                }
                if (prevDesc.get || prevDesc.set) {
                    // get and set are defined together. If they are both defined
                    // in the previous descriptor but only one in the new descriptor
                    // then the other will be undefined so we need to apply the
                    // previous descriptor in the new one.
                    newDesc.get = newDesc.get || prevDesc.get;
                    newDesc.set = newDesc.set || prevDesc.set;
                    if (prevDesc.get && typeof newDesc.get === "function") {
                        makeIntermediateFunction("get", prevDesc, newDesc, patchedFnName);
                    }
                    if (prevDesc.set && typeof newDesc.set === "function") {
                        makeIntermediateFunction("set", prevDesc, newDesc, patchedFnName);
                    }
                }
            }

            Object.defineProperty(obj, k, newDesc);
        }

        function makeIntermediateFunction(key, prevDesc, newDesc, patchedFnName) {
            const _superFn = prevDesc[key];
            const patchFn = newDesc[key];
            newDesc[key] = {
                [patchedFnName](...args) {
                    const prevSuper = this._super;
                    this._super = _superFn.bind(this);
                    const result = patchFn.call(this, ...args);
                    this._super = prevSuper;
                    return result;
                }
            }[patchedFnName];
        }
    },
    /**
     * performs a half up rounding with a fixed amount of decimals, correcting for float loss of precision
     * See the corresponding float_round() in server/tools/float_utils.py for more info
     * @param {Number} value the value to be rounded
     * @param {Number} decimals the number of decimals. eg: round_decimals(3.141592,2) -> 3.14
     */
    round_decimals: function (value, decimals) {
        /**
         * The following decimals introduce numerical errors:
         * Math.pow(10, -4) = 0.00009999999999999999
         * Math.pow(10, -5) = 0.000009999999999999999
         *
         * Such errors will propagate in round_precision and lead to inconsistencies between Python
         * and JavaScript. To avoid this, we parse the scientific notation.
         */
        return utils.round_precision(value, parseFloat('1e' + -decimals));
    },
    /**
     * performs a half up rounding with arbitrary precision, correcting for float loss of precision
     * See the corresponding float_round() in server/tools/float_utils.py for more info
     *
     * @param {number} value the value to be rounded
     * @param {number} precision a precision parameter. eg: 0.01 rounds to two digits.
     */
    round_precision: function (value, precision) {
        if (!value) {
            return 0;
        } else if (!precision || precision < 0) {
            precision = 1;
        }
        var normalized_value = value / precision;
        var epsilon_magnitude = Math.log(Math.abs(normalized_value))/Math.log(2);
        var epsilon = Math.pow(2, epsilon_magnitude - 52);
        normalized_value += normalized_value >= 0 ? epsilon : -epsilon;

        /**
         * Javascript performs strictly the round half up method, which is asymmetric. However, in
         * Python, the method is symmetric. For example:
         * - In JS, Math.round(-0.5) is equal to -0.
         * - In Python, round(-0.5) is equal to -1.
         * We want to keep the Python behavior for consistency.
         */
        var sign = normalized_value < 0 ? -1.0 : 1.0;
        var rounded_value = sign * Math.round(Math.abs(normalized_value));
        return rounded_value * precision;
    },
    /**
     * @see lpad
     *
     * @param {string} str
     * @param {number} size
     * @returns {string}
     */
    rpad: function (str, size) {
        str = "" + str;
        return str + new Array(size - str.length + 1).join('0');
    },
    /**
     * Return a shallow copy of a given array sorted by a given criterion or a default one.
     * The given criterion can either be:
     * - a string: a property name on the array elements returning the sortable primitive
     * - a function: a handler that will return the sortable primitive from a given element.
     *
     * @param {any[]} array
     * @param {string | function} [criterion]
     * @param {('asc' | 'desc')} [order='asc'] sort by ascending if order is 'asc' else descending
     */
    sortBy: function (array, criterion, order = 'asc') {
        const extract = _getExtractorFrom(criterion);
        return array.slice().sort((elA, elB) => {
            const a = extract(elA);
            const b = extract(elB);
            let result;
            if (isNaN(a) && isNaN(b)) {
                result = a > b ? 1 : a < b ? -1 : 0;
            } else {
                result = a - b;
            }
            return order === 'asc' ? result : -result;
        });
    },
    /**
     * Returns a string formatted using given values.
     *
     * If the value is an object, its keys will replace `%(key)s` expressions.
     * If the values are a set of strings, they will replace `%s` expressions.
     * If no value is given, the string will not be formatted.
     *
     * `Markup`-aware: if a `Markup` object is provided as format string,
     * automatically escapes injected values and returns a new `Markup`
     * object.
     *
     * @param {string|Markup} string format string
     * @param values values injected into the format string, can be either a
     *               sequence of positional parameters (for positional
     *               placeholders) or a single Object acting a as map (for named
     *               placeholders).
     * @returns {string|Markup}
     */
    sprintf(string, ...values) {
        let finalizer, mapper;
        finalizer = mapper = a => a;
        if (string instanceof _Markup) {
            string = String(string);
            finalizer = Markup;
            mapper = _.escape;
        }
        if (values.length === 1 && typeof values[0] === 'object') {
            const valuesDict = values[0];
            string = string.replace(
                /%\((\w+)\)s/g,
                (_, group) => mapper(valuesDict[group]));
        } else {
            let i = 0;
            string = string.replace(/%s/g, () => mapper(values[i++]));
        }
        return finalizer(string);
    },
    /**
     * Sort an array in place, keeping the initial order for identical values.
     *
     * @param {Array} array
     * @param {function} iteratee
     */
    stableSort: function (array, iteratee) {
        var stable = array.slice();
        return array.sort(function stableCompare (a, b) {
            var order = iteratee(a, b);
            if (order !== 0) {
                return order;
            } else {
                return stable.indexOf(a) - stable.indexOf(b);
            }
        });
    },
    /**
     * @param {any} array
     * @param {any} elem1
     * @param {any} elem2
     */
    swap: function (array, elem1, elem2) {
        var i1 = array.indexOf(elem1);
        var i2 = array.indexOf(elem2);
        array[i2] = elem1;
        array[i1] = elem2;
    },

    /**
     * @param {string} value
     * @param {boolean} allow_mailto
     * @returns boolean
     */
    is_email: function (value, allow_mailto) {
        // http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
        var re;
        if (allow_mailto) {
            re = /^(mailto:)?(([^<>()\[\]\.,;:\s@\"]+(\.[^<>()\[\]\.,;:\s@\"]+)*)|(\".+\"))@(([^<>()[\]\.,;:\s@\"]+\.)+[^<>()[\]\.,;:\s@\"]{2,})$/i;
        } else {
            re = /^(([^<>()\[\]\.,;:\s@\"]+(\.[^<>()\[\]\.,;:\s@\"]+)*)|(\".+\"))@(([^<>()[\]\.,;:\s@\"]+\.)+[^<>()[\]\.,;:\s@\"]{2,})$/i;
        }
        return re.test(value);
    },

    /**
     * @param {any} str
     * @param {any} elseValues
     * @param {any} trueValues
     * @param {any} falseValues
     * @returns
     */
    toBoolElse: function (str, elseValues, trueValues, falseValues) {
        var ret = _.str.toBool(str, trueValues, falseValues);
        if (_.isUndefined(ret)) {
            return elseValues;
        }
        return ret;
    },
    /**
     * @todo: is this really the correct place?
     *
     * @param {any} data
     * @param {any} f
     */
    traverse_records: function (data, f) {
        if (data.type === 'record') {
            f(data);
        } else if (data.data) {
            for (var i = 0; i < data.data.length; i++) {
                utils.traverse_records(data.data[i], f);
            }
        }
    },
    /**
     * Replace diacritics character with ASCII character
     *
     * @param {string} str diacritics string
     * @param {boolean} casesensetive
     * @returns {string} ASCII string
     */
    unaccent: function (str, casesensetive) {
        str = str.replace(/[^\u0000-\u007E]/g, function (accented) {
            return diacriticsMap[accented] || accented;
        });
        return casesensetive ? str : str.toLowerCase();
    },
    /**
     * We define here an unpatch function.  This is mostly useful if we want to
     * remove a patch.  For example, for testing purposes
     *
     * @param {Object} obj
     * @param {string} patchName
     * @returns {Object} the removed patch
     */
    unpatch: function (obj, patchName) {
        const objDesc = patchMap.get(obj);
        if (!objDesc || !objDesc.patches.some(p => p.name === patchName)) {
            throw new UnknownPatchError(`Could not find patch ${patchName}`);
        }
        patchMap.delete(obj);

        // Restore original methods on the prototype and the class.
        for (const k in objDesc.original) {
            if (objDesc.original[k] === undefined) {
                delete obj[k];
            } else {
                Object.defineProperty(obj, k, objDesc.original[k]);
            }
        }

        // Re-apply the patches except the one to remove.
        let removedPatch;
        for (const patchDesc of objDesc.patches) {
            if (patchDesc.name !== patchName) {
                utils.patch(obj, patchDesc.name, patchDesc.patch);
            } else {
                removedPatch = patchDesc.patch;
            }
        }

        return removedPatch;
    },
    /**
     * @param {any} node
     * @param {any} strip_whitespace
     * @returns
     */
    xml_to_json: function (node, strip_whitespace) {
        switch (node.nodeType) {
            case 9:
                return utils.xml_to_json(node.documentElement, strip_whitespace);
            case 3:
            case 4:
                return (strip_whitespace && node.data.trim() === '') ? undefined : node.data;
            case 1:
                var attrs = $(node).getAttributes();
                return {
                    tag: node.tagName.toLowerCase(),
                    attrs: attrs,
                    children: _.compact(_.map(node.childNodes, function (node) {
                        return utils.xml_to_json(node, strip_whitespace);
                    })),
                };
        }
    },
    /**
     * @param {any} node
     * @returns {string}
     */
    xml_to_str: function (node) {
        var str = "";
        if (window.XMLSerializer) {
            str = (new XMLSerializer()).serializeToString(node);
        } else if (window.ActiveXObject) {
            str = node.xml;
        } else {
            throw new Error(_t("Could not serialize XML"));
        }
        // Browsers won't deal with self closing tags except void elements:
        // http://www.w3.org/TR/html-markup/syntax.html
        var void_elements = 'area base br col command embed hr img input keygen link meta param source track wbr'.split(' ');

        // The following regex is a bit naive but it's ok for the xmlserializer output
        str = str.replace(/<([a-z]+)([^<>]*)\s*\/\s*>/g, function (match, tag, attrs) {
            if (void_elements.indexOf(tag) < 0) {
                return "<" + tag + attrs + "></" + tag + ">";
            } else {
                return match;
            }
        });
        return str;
    },
    /**
     * Visit a tree of objects, where each children are in an attribute 'children'.
     * For each children, we call the callback function given in arguments.
     *
     * @param {Object} tree an object describing a tree structure
     * @param {function} f a callback
     */
    traverse: function (tree, f) {
        if (f(tree)) {
            _.each(tree.children, function (c) { utils.traverse(c, f); });
        }
    },
    /**
     * Enhanced traverse function with 'path' building on traverse.
     *
     * @param {Object} tree an object describing a tree structure
     * @param {function} f a callback
     * @param {Object} path the path to the current 'tree' object
     */
    traversePath: function (tree, f, path) {
        path = path || [];
        f(tree, path);
        _.each(tree.children, function (node) {
            utils.traversePath(node, f, path.concat(tree));
        });
    },
    /**
     * Visit a tree of objects and freeze all
     *
     * @param {Object} obj
     */
    deepFreeze: function (obj) {
      var propNames = Object.getOwnPropertyNames(obj);
      propNames.forEach(function(name) {
        var prop = obj[name];
        if (typeof prop == 'object' && prop !== null)
          utils.deepFreeze(prop);
      });
      return Object.freeze(obj);
    },

    /**
     * Find the closest value of the given one in the provided array
     *
     * @param {Number} num
     * @param {Array} arr
     * @returns {Number|undefined}
     */
    closestNumber: function (num, arr) {
        var curr = arr[0];
        var diff = Math.abs (num - curr);
        for (var val = 0; val < arr.length; val++) {
            var newdiff = Math.abs (num - arr[val]);
            if (newdiff < diff) {
                diff = newdiff;
                curr = arr[val];
            }
        }
        return curr;
    },
};

return utils;

});
