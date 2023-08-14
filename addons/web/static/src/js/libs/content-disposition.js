/*
(The MIT License)

Copyright (c) 2014-2017 Douglas Christopher Wilson

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

/**
 * Stripped down to only parsing/decoding.
 */
odoo.define('web.contentdisposition', function () {
'use strict';

/**
 * RegExp to match percent encoding escape.
 * @private
 */
var HEX_ESCAPE_REPLACE_REGEXP = /%([0-9A-Fa-f]{2})/g;

/**
 * RegExp to match non-latin1 characters.
 * @private
 */
var NON_LATIN1_REGEXP = /[^\x20-\x7e\xa0-\xff]/g;

/**
 * RegExp to match quoted-pair in RFC 2616
 *
 * quoted-pair = "\" CHAR
 * CHAR        = <any US-ASCII character (octets 0 - 127)>
 * @private
 */
var QESC_REGEXP = /\\([\u0000-\u007f])/g;

/**
 * RegExp for various RFC 2616 grammar
 *
 * parameter     = token "=" ( token | quoted-string )
 * token         = 1*<any CHAR except CTLs or separators>
 * separators    = "(" | ")" | "<" | ">" | "@"
 *               | "," | ";" | ":" | "\" | <">
 *               | "/" | "[" | "]" | "?" | "="
 *               | "{" | "}" | SP | HT
 * quoted-string = ( <"> *(qdtext | quoted-pair ) <"> )
 * qdtext        = <any TEXT except <">>
 * quoted-pair   = "\" CHAR
 * CHAR          = <any US-ASCII character (octets 0 - 127)>
 * TEXT          = <any OCTET except CTLs, but including LWS>
 * LWS           = [CRLF] 1*( SP | HT )
 * CRLF          = CR LF
 * CR            = <US-ASCII CR, carriage return (13)>
 * LF            = <US-ASCII LF, linefeed (10)>
 * SP            = <US-ASCII SP, space (32)>
 * HT            = <US-ASCII HT, horizontal-tab (9)>
 * CTL           = <any US-ASCII control character (octets 0 - 31) and DEL (127)>
 * OCTET         = <any 8-bit sequence of data>
 * @private
 */
var PARAM_REGEXP = /;[\x09\x20]*([!#$%&'*+.0-9A-Z^_`a-z|~-]+)[\x09\x20]*=[\x09\x20]*("(?:[\x20!\x23-\x5b\x5d-\x7e\x80-\xff]|\\[\x20-\x7e])*"|[!#$%&'*+.0-9A-Z^_`a-z|~-]+)[\x09\x20]*/g;

/**
 * RegExp for various RFC 5987 grammar
 *
 * ext-value     = charset  "'" [ language ] "'" value-chars
 * charset       = "UTF-8" / "ISO-8859-1" / mime-charset
 * mime-charset  = 1*mime-charsetc
 * mime-charsetc = ALPHA / DIGIT
 *               / "!" / "#" / "$" / "%" / "&"
 *               / "+" / "-" / "^" / "_" / "`"
 *               / "{" / "}" / "~"
 * language      = ( 2*3ALPHA [ extlang ] )
 *               / 4ALPHA
 *               / 5*8ALPHA
 * extlang       = *3( "-" 3ALPHA )
 * value-chars   = *( pct-encoded / attr-char )
 * pct-encoded   = "%" HEXDIG HEXDIG
 * attr-char     = ALPHA / DIGIT
 *               / "!" / "#" / "$" / "&" / "+" / "-" / "."
 *               / "^" / "_" / "`" / "|" / "~"
 * @private
 */
var EXT_VALUE_REGEXP = /^([A-Za-z0-9!#$%&+\-^_`{}~]+)'(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}|[A-Za-z]{4,8}|)'((?:%[0-9A-Fa-f]{2}|[A-Za-z0-9!#$&+.^_`|~-])+)$/;

/**
 * RegExp for various RFC 6266 grammar
 *
 * disposition-type = "inline" | "attachment" | disp-ext-type
 * disp-ext-type    = token
 * disposition-parm = filename-parm | disp-ext-parm
 * filename-parm    = "filename" "=" value
 *                  | "filename*" "=" ext-value
 * disp-ext-parm    = token "=" value
 *                  | ext-token "=" ext-value
 * ext-token        = <the characters in token, followed by "*">
 * @private
 */
var DISPOSITION_TYPE_REGEXP = /^([!#$%&'*+.0-9A-Z^_`a-z|~-]+)[\x09\x20]*(?:$|;)/;

/**
 * Decode a RFC 6987 field value (gracefully).
 *
 * @param {string} str
 * @return {string}
 * @private
 */
function decodefield(str) {
    var match = EXT_VALUE_REGEXP.exec(str);

    if (!match) {
        throw new TypeError('invalid extended field value')
    }

    var charset = match[1].toLowerCase();
    var encoded = match[2];

    switch (charset) {
    case 'iso-8859-1':
        return encoded.replace(HEX_ESCAPE_REPLACE_REGEXP, pdecode).replace(NON_LATIN1_REGEXP, '?');
    case 'utf-8':
        return decodeURIComponent(encoded);
    default:
        throw new TypeError('unsupported charset in extended field')
    }
}

/**
 * Parse Content-Disposition header string.
 *
 * @param {string} string
 * @return {ContentDisposition}
 * @public
 */
function parse(string) {
    if (!string || typeof string !== 'string') {
        throw new TypeError('argument string is required')
    }

    var match = DISPOSITION_TYPE_REGEXP.exec(string);

    if (!match) {
        throw new TypeError('invalid type format')
    }

    // normalize type
    var index = match[0].length;
    var type = match[1].toLowerCase();

    var key;
    var names = [];
    var params = {};
    var value;

    // calculate index to start at
    index = PARAM_REGEXP.lastIndex = match[0].substr(-1) === ';' ? index - 1 : index;

    // match parameters
    while ((match = PARAM_REGEXP.exec(string))) {
        if (match.index !== index) {
            throw new TypeError('invalid parameter format')
        }

        index += match[0].length;
        key = match[1].toLowerCase();
        value = match[2];

        if (names.indexOf(key) !== -1) {
            throw new TypeError('invalid duplicate parameter')
        }

        names.push(key);

        if (key.indexOf('*') + 1 === key.length) {
            // decode extended value
            key = key.slice(0, -1);
            value = decodefield(value);

            // overwrite existing value
            params[key] = value;
            continue
        }

        if (typeof params[key] === 'string') {
            continue
        }

        if (value[0] === '"') {
            // remove quotes and escapes
            value = value
                    .substr(1, value.length - 2)
                    .replace(QESC_REGEXP, '$1')
        }

        params[key] = value
    }

    if (index !== -1 && index !== string.length) {
        throw new TypeError('invalid parameter format')
    }

    return new ContentDisposition(type, params)
}

/**
 * Percent decode a single character.
 *
 * @param {string} str
 * @param {string} hex
 * @return {string}
 * @private
 */
function pdecode(str, hex) {
    return String.fromCharCode(parseInt(hex, 16))
}

/**
 * Class for parsed Content-Disposition header for v8 optimization
 *
 * @public
 * @param {string} type
 * @param {object} parameters
 * @constructor
 */
function ContentDisposition(type, parameters) {
    this.type = type;
    this.parameters = parameters
}

return {
    parse: parse,
};
});
