/** @odoo-module **/

export const nbsp = "\u00a0";

export const escapeMethod = Symbol("html");

/**
 * Escapes a string for HTML.
 *
 * @param {string | number} [str] the string to escape
 * @returns {string} an escaped string
 */
export function escape(str) {
    if (typeof str === "object" && str[escapeMethod]) {
        return str[escapeMethod]();
    } else {
        if (str === undefined) {
            return "";
        }
        if (typeof str === "number") {
            return String(str);
        }
        [
            ["&", "&amp;"],
            ["<", "&lt;"],
            [">", "&gt;"],
            ["'", "&#x27;"],
            ['"', "&quot;"],
            ["`", "&#x60;"],
        ].forEach((pairs) => {
            str = String(str).replaceAll(pairs[0], pairs[1]);
        });
        return str;
    }
}

/**
 * Escapes a string to use as a RegExp.
 * @url https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions#Escaping
 *
 * @param {string} str
 * @returns {string} escaped string to use as a RegExp
 */
export function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

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
 * @param {string} str
 * @param {number[]} indices
 * @param {string} separator
 * @returns {string}
 */
export function intersperse(str, indices, separator = "") {
    separator = separator || "";
    const result = [];
    let last = str.length;
    for (let i = 0; i < indices.length; ++i) {
        let section = indices[i];
        if (section === -1 || last <= 0) {
            // Done with string, or -1 (stops formatting string)
            break;
        } else if (section === 0 && i === 0) {
            // repeats previous section, which there is none => stop
            break;
        } else if (section === 0) {
            // repeat previous section forever
            //noinspection AssignmentToForLoopParameterJS
            section = indices[--i];
        }
        result.push(str.substring(last - section, last));
        last -= section;
    }
    const s = str.substring(0, last);
    if (s) {
        result.push(s);
    }
    return result.reverse().join(separator);
}

/**
 * Returns a string formatted using given values.
 * If the value is an object, its keys will replace `%(key)s` expressions.
 * If the values are a set of strings, they will replace `%s` expressions.
 * If no value is given, the string will not be formatted.
 *
 * @param {string} s
 * @param {any[]} values
 * @returns {string}
 */
export function sprintf(s, ...values) {
    if (values.length === 1 && Object.prototype.toString.call(values[0]) === "[object Object]") {
        const valuesDict = values[0];
        s = s.replace(/%\(([^)]+)\)s/g, (match, value) => valuesDict[value]);
    } else if (values.length > 0) {
        s = s.replace(/%s/g, () => values.shift());
    }
    return s;
}

/**
 * Capitalizes a string: "abc def" => "Abc def"
 *
 * @param {string} s the input string
 * @returns {string}
 */
export function capitalize(s) {
    return s ? s[0].toUpperCase() + s.slice(1) : "";
}

/* eslint-disable */
// prettier-ignore
const diacriticsMap = {
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

/**
 * Replace diacritics character with ASCII character
 *
 * @param {string} str diacritics string
 * @param {boolean} caseSensitive
 * @returns {string} ASCII string
 */
export function unaccent(str, caseSensitive) {
    str = str.replace(/[^\u0000-\u007E]/g, function (accented) {
        return diacriticsMap[accented] || accented;
    });
    return caseSensitive ? str : str.toLowerCase();
}

/**
 * @param {string} value
 * @returns boolean
 */
export function isEmail(value) {
    // http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
    const re = /^(([^<>()\[\]\.,;:\s@\"]+(\.[^<>()\[\]\.,;:\s@\"]+)*)|(\".+\"))@(([^<>()[\]\.,;:\s@\"]+\.)+[^<>()[\]\.,;:\s@\"]{2,})$/i;
    return re.test(value);
}
