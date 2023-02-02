/** @odoo-module **/

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef {{type: 0, value: number}} TokenNumber
 *
 * @typedef {{type: 1, value: string}} TokenString
 *
 * @typedef {{type: 2, value: string}} TokenSymbol
 *
 * @typedef {{type: 3, value: string}} TokenName
 *
 * @typedef {{type: 4, value: string}} TokenConstant
 *
 * @typedef {TokenNumber | TokenString | TokenSymbol | TokenName | TokenConstant} Token
 */

export class TokenizerError extends Error {}

// -----------------------------------------------------------------------------
// Helpers and Constants
// -----------------------------------------------------------------------------

/**
 * Directly maps a single escape code to an output character
 */
const directMap = {
    "\\": "\\",
    '"': '"',
    "'": "'",
    a: "\x07",
    b: "\x08",
    f: "\x0c",
    n: "\n",
    r: "\r",
    t: "\t",
    v: "\v",
};

/**
 * Implements the decoding of Python string literals (embedded in
 * JS strings) into actual JS strings. This includes the decoding
 * of escapes into their corresponding JS
 * characters/codepoints/whatever.
 *
 * The ``unicode`` flags notes whether the literal should be
 * decoded as a bytestring literal or a unicode literal, which
 * pretty much only impacts decoding (or not) of unicode escapes
 * at this point since bytestrings are not technically handled
 * (everything is decoded to JS "unicode" strings)
 *
 * Eventurally, ``str`` could eventually use typed arrays, that'd
 * be interesting...
 *
 * @param {string} str
 * @param {boolean} unicode
 * @returns {string}
 */
function decodeStringLiteral(str, unicode) {
    const out = [];
    let code;
    for (var i = 0; i < str.length; ++i) {
        if (str[i] !== "\\") {
            out.push(str[i]);
            continue;
        }
        var escape = str[i + 1];
        if (escape in directMap) {
            out.push(directMap[escape]);
            ++i;
            continue;
        }
        switch (escape) {
            // Ignored
            case "\n":
                ++i;
                continue;
            // Character named name in the Unicode database (Unicode only)
            case "N":
                if (!unicode) {
                    break;
                }
                throw new TokenizerError("SyntaxError: \\N{} escape not implemented");
            case "u":
                if (!unicode) {
                    break;
                }
                var uni = str.slice(i + 2, i + 6);
                if (!/[0-9a-f]{4}/i.test(uni)) {
                    throw new TokenizerError(
                        [
                            "SyntaxError: (unicode error) 'unicodeescape' codec",
                            " can't decode bytes in position ",
                            i,
                            "-",
                            i + 4,
                            ": truncated \\uXXXX escape",
                        ].join("")
                    );
                }
                code = parseInt(uni, 16);
                out.push(String.fromCharCode(code));
                // escape + 4 hex digits
                i += 5;
                continue;
            case "U":
                if (!unicode) {
                    break;
                }
                // TODO: String.fromCodePoint
                throw new TokenizerError("SyntaxError: \\U escape not implemented");
            case "x":
                // get 2 hex digits
                var hex = str.slice(i + 2, i + 4);
                if (!/[0-9a-f]{2}/i.test(hex)) {
                    if (!unicode) {
                        throw new TokenizerError("ValueError: invalid \\x escape");
                    }
                    throw new TokenizerError(
                        [
                            "SyntaxError: (unicode error) 'unicodeescape'",
                            " codec can't decode bytes in position ",
                            i,
                            "-",
                            i + 2,
                            ": truncated \\xXX escape",
                        ].join("")
                    );
                }
                code = parseInt(hex, 16);
                out.push(String.fromCharCode(code));
                // skip escape + 2 hex digits
                i += 3;
                continue;
            default:
                // Check if octal
                if (!/[0-8]/.test(escape)) {
                    break;
                }
                var r = /[0-8]{1,3}/g;
                r.lastIndex = i + 1;
                var m = r.exec(str);
                var oct = m[0];
                code = parseInt(oct, 8);
                out.push(String.fromCharCode(code));
                // skip matchlength
                i += oct.length;
                continue;
        }
        out.push("\\");
    }
    return out.join("");
}

const constants = new Set(["None", "False", "True"]);

export const comparators = [
    "in",
    "not",
    "not in",
    "is",
    "is not",
    "<",
    "<=",
    ">",
    ">=",
    "<>",
    "!=",
    "==",
];

export const binaryOperators = [
    "or",
    "and",
    "|",
    "^",
    "&",
    "<<",
    ">>",
    "+",
    "-",
    "*",
    "/",
    "//",
    "%",
    "~",
    "**",
    ".",
];

export const unaryOperators = ["-"];

const symbols = new Set([
    ...["(", ")", "[", "]", "{", "}", ":", ","],
    ...["if", "else", "lambda", "="],
    ...comparators,
    ...binaryOperators,
    ...unaryOperators,
]);

// Regexps
function group(...args) {
    return "(" + args.join("|") + ")";
}

const Name = "[a-zA-Z_]\\w*";
const Whitespace = "[ \\f\\t]*";
const DecNumber = "\\d+(L|l)?";
const IntNumber = DecNumber;

const Exponent = "[eE][+-]?\\d+";
const PointFloat = group(`\\d+\\.\\d*(${Exponent})?`, `\\.\\d+(${Exponent})?`);
// Exponent not optional when no decimal point
const FloatNumber = group(PointFloat, `\\d+${Exponent}`);

const Number = group(FloatNumber, IntNumber);
const Operator = group("\\*\\*=?", ">>=?", "<<=?", "<>", "!=", "//=?", "[+\\-*/%&|^=<>]=?", "~");
const Bracket = "[\\[\\]\\(\\)\\{\\}]";
const Special = "[:;.,`@]";
const Funny = group(Operator, Bracket, Special);
const ContStr = group(
    "([uU])?'([^\n'\\\\]*(?:\\\\.[^\n'\\\\]*)*)'",
    '([uU])?"([^\n"\\\\]*(?:\\\\.[^\n"\\\\]*)*)"'
);
const PseudoToken = Whitespace + group(Number, Funny, ContStr, Name);
const NumberPattern = new RegExp("^" + Number + "$");
const StringPattern = new RegExp("^" + ContStr + "$");
const NamePattern = new RegExp("^" + Name + "$");
const strip = new RegExp("^" + Whitespace);

// -----------------------------------------------------------------------------
// Tokenize function
// -----------------------------------------------------------------------------

/**
 * Transform a string into a list of tokens
 *
 * @param {string} str
 * @returns {Token[]}
 */
export function tokenize(str) {
    const tokens = [];
    const max = str.length;
    let start = 0;
    let end = 0;
    // /g flag makes repeated exec() have memory
    const pseudoprog = new RegExp(PseudoToken, "g");
    while (pseudoprog.lastIndex < max) {
        const pseudomatch = pseudoprog.exec(str);
        if (!pseudomatch) {
            // if match failed on trailing whitespace, end tokenizing
            if (/^\s+$/.test(str.slice(end))) {
                break;
            }
            throw new TokenizerError(
                "Failed to tokenize <<" +
                    str +
                    ">> at index " +
                    (end || 0) +
                    "; parsed so far: " +
                    tokens
            );
        }
        if (pseudomatch.index > end) {
            if (str.slice(end, pseudomatch.index).trim()) {
                throw new TokenizerError("Invalid expression");
            }
        }
        start = pseudomatch.index;
        end = pseudoprog.lastIndex;
        let token = str.slice(start, end).replace(strip, "");
        if (NumberPattern.test(token)) {
            tokens.push({
                type: 0 /* Number */,
                value: parseFloat(token),
            });
        } else if (StringPattern.test(token)) {
            var m = StringPattern.exec(token);
            tokens.push({
                type: 1 /* String */,
                value: decodeStringLiteral(m[3] !== undefined ? m[3] : m[5], !!(m[2] || m[4])),
            });
        } else if (symbols.has(token)) {
            // transform 'not in' and 'is not' in a single token
            if (token === "in" && tokens.length > 0 && tokens[tokens.length - 1].value === "not") {
                token = "not in";
                tokens.pop();
            } else if (
                token === "not" &&
                tokens.length > 0 &&
                tokens[tokens.length - 1].value === "is"
            ) {
                token = "is not";
                tokens.pop();
            }
            tokens.push({
                type: 2 /* Symbol */,
                value: token,
            });
        } else if (constants.has(token)) {
            tokens.push({
                type: 4 /* Constant */,
                value: token,
            });
        } else if (NamePattern.test(token)) {
            tokens.push({
                type: 3 /* Name */,
                value: token,
            });
        } else {
            throw new TokenizerError("Invalid expression");
        }
    }
    return tokens;
}
