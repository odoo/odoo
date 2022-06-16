/** @odoo-module **/

import { binaryOperators, comparators } from "./py_tokenizer";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef { import("./py_tokenizer").Token } Token
 */

/**
 * @typedef {{type: 0, value: number}} ASTNumber
 * @typedef {{type: 1, value: string}} ASTString
 * @typedef {{type: 2, value: boolean}} ASTBoolean
 * @typedef {{type: 3}} ASTNone
 * @typedef {{type: 4, value: AST[]}} ASTList
 * @typedef {{type: 5, value: string}} ASTName
 * @typedef {{type: 6, op: string, right: AST}} ASTUnaryOperator
 * @typedef {{type: 7, op: string, left: AST, right: AST}} ASTBinaryOperator
 * @typedef {{type: 8, fn: AST, args: AST[], kwargs: {[key: string]: AST}}} ASTFunctionCall
 * @typedef {{type: 9, name: ASTName, value: AST}} ASTAssignment
 * @typedef {{type: 10, value: AST[]}} ASTTuple
 * @typedef {{type: 11, value: { [key: string]: AST}}} ASTDictionary
 * @typedef {{type: 12, target: AST, key: AST}} ASTLookup
 * @typedef {{type: 13, condition: AST, ifTrue: AST, ifFalse: AST}} ASTIf
 * @typedef {{type: 14, op: string, left: AST, right: AST}} ASTBooleanOperator
 * @typedef {{type: 15, obj: AST, key: string}} ASTObjLookup
 *
 * @typedef { ASTNumber | ASTString | ASTBoolean | ASTNone | ASTList | ASTName | ASTUnaryOperator | ASTBinaryOperator | ASTFunctionCall | ASTAssignment | ASTTuple | ASTDictionary |ASTLookup | ASTIf | ASTBooleanOperator | ASTObjLookup} AST
 */

export class ParserError extends Error {}

// -----------------------------------------------------------------------------
// Constants and helpers
// -----------------------------------------------------------------------------

const chainedOperators = new Set(comparators);
const infixOperators = new Set(binaryOperators.concat(comparators));

/**
 * Compute the "binding power" of a symbol
 *
 * @param {string} symbol
 * @returns {number}
 */
export function bp(symbol) {
    switch (symbol) {
        case "=":
            return 10;
        case "if":
            return 20;
        case "in":
        case "not in":
        case "is":
        case "is not":
        case "<":
        case "<=":
        case ">":
        case ">=":
        case "<>":
        case "==":
        case "!=":
            return 60;
        case "or":
            return 30;
        case "and":
            return 40;
        case "not":
            return 50;
        case "|":
            return 70;
        case "^":
            return 80;
        case "&":
            return 90;
        case "<<":
        case ">>":
            return 100;
        case "+":
        case "-":
            return 110;
        case "*":
        case "/":
        case "//":
        case "%":
            return 120;
        case "**":
            return 140;
        case ".":
        case "(":
        case "[":
            return 150;
    }
    return 0;
}

/**
 * Compute binding power of a symbol
 *
 * @param {Token} token
 * @returns {number}
 */
function bindingPower(token) {
    return token.type === 2 /* Symbol */ ? bp(token.value) : 0;
}

/**
 * Check if a token is a symbol of a given value
 *
 * @param {Token} token
 * @param {string} value
 * @returns {boolean}
 */
function isSymbol(token, value) {
    return token.type === 2 /* Symbol */ && token.value === value;
}

/**
 * @param {Token} current
 * @param {Token[]} tokens
 * @returns {AST}
 */
function parsePrefix(current, tokens) {
    switch (current.type) {
        case 0 /* Number */:
            return { type: 0 /* Number */, value: current.value };
        case 1 /* String */:
            return { type: 1 /* String */, value: current.value };
        case 4 /* Constant */:
            if (current.value === "None") {
                return { type: 3 /* None */ };
            } else {
                return { type: 2 /* Boolean */, value: current.value === "True" };
            }
        case 3 /* Name */:
            return { type: 5 /* Name */, value: current.value };
        case 2 /* Symbol */:
            switch (current.value) {
                case "-":
                case "+":
                case "~":
                    return {
                        type: 6 /* UnaryOperator */,
                        op: current.value,
                        right: _parse(tokens, 130),
                    };
                case "not":
                    return {
                        type: 6 /* UnaryOperator */,
                        op: current.value,
                        right: _parse(tokens, 50),
                    };
                case "(":
                    const content = [];
                    let isTuple = false;
                    while (tokens[0] && !isSymbol(tokens[0], ")")) {
                        content.push(_parse(tokens, 0));
                        if (tokens[0]) {
                            if (tokens[0] && isSymbol(tokens[0], ",")) {
                                isTuple = true;
                                tokens.shift();
                            } else if (!isSymbol(tokens[0], ")")) {
                                throw new ParserError("parsing error");
                            }
                        } else {
                            throw new ParserError("parsing error");
                        }
                    }
                    if (!tokens[0] || !isSymbol(tokens[0], ")")) {
                        throw new ParserError("parsing error");
                    }
                    tokens.shift();
                    isTuple = isTuple || content.length === 0;
                    return isTuple ? { type: 10 /* Tuple */, value: content } : content[0];
                case "[":
                    const value = [];
                    while (tokens[0] && !isSymbol(tokens[0], "]")) {
                        value.push(_parse(tokens, 0));
                        if (tokens[0]) {
                            if (isSymbol(tokens[0], ",")) {
                                tokens.shift();
                            } else if (!isSymbol(tokens[0], "]")) {
                                throw new ParserError("parsing error");
                            }
                        }
                    }
                    if (!tokens[0] || !isSymbol(tokens[0], "]")) {
                        throw new ParserError("parsing error");
                    }
                    tokens.shift();
                    return { type: 4 /* List */, value };
                case "{": {
                    const dict = {};
                    while (tokens[0] && !isSymbol(tokens[0], "}")) {
                        const key = _parse(tokens, 0);
                        if (
                            (key.type !== 1 /* String */ && key.type !== 0) /* Number */ ||
                            !tokens[0] ||
                            !isSymbol(tokens[0], ":")
                        ) {
                            throw new ParserError("parsing error");
                        }
                        tokens.shift();
                        const value = _parse(tokens, 0);
                        dict[key.value] = value;
                        if (isSymbol(tokens[0], ",")) {
                            tokens.shift();
                        }
                    }
                    // remove the } token
                    if (!tokens.shift()) {
                        throw new ParserError("parsing error");
                    }
                    return { type: 11 /* Dictionary */, value: dict };
                }
            }
    }
    throw new ParserError("Token cannot be parsed");
}

/**
 * @param {AST} ast
 * @param {Token} current
 * @param {Token[]} tokens
 * @returns {AST}
 */
function parseInfix(left, current, tokens) {
    switch (current.type) {
        case 2 /* Symbol */:
            if (infixOperators.has(current.value)) {
                let right = _parse(tokens, bindingPower(current));
                if (current.value === "and" || current.value === "or") {
                    return {
                        type: 14 /* BooleanOperator */,
                        op: current.value,
                        left,
                        right,
                    };
                } else if (current.value === ".") {
                    if (right.type === 5 /* Name */) {
                        return {
                            type: 15 /* ObjLookup */,
                            obj: left,
                            key: right.value,
                        };
                    } else {
                        throw new ParserError("invalid obj lookup");
                    }
                }
                let op = {
                    type: 7 /* BinaryOperator */,
                    op: current.value,
                    left,
                    right,
                };
                while (
                    chainedOperators.has(current.value) &&
                    tokens[0] &&
                    tokens[0].type === 2 /* Symbol */ &&
                    chainedOperators.has(tokens[0].value)
                ) {
                    const nextToken = tokens.shift();
                    op = {
                        type: 14 /* BooleanOperator */,
                        op: "and",
                        left: op,
                        right: {
                            type: 7 /* BinaryOperator */,
                            op: nextToken.value,
                            left: right,
                            right: _parse(tokens, bindingPower(nextToken)),
                        },
                    };
                    right = op.right.right;
                }
                return op;
            }
            switch (current.value) {
                case "(":
                    // function call
                    const args = [];
                    const kwargs = {};
                    while (tokens[0] && !isSymbol(tokens[0], ")")) {
                        const arg = _parse(tokens, 0);
                        if (arg.type === 9 /* Assignment */) {
                            kwargs[arg.name.value] = arg.value;
                        } else {
                            args.push(arg);
                        }
                        if (tokens[0] && isSymbol(tokens[0], ",")) {
                            tokens.shift();
                        }
                    }
                    if (!tokens[0] || !isSymbol(tokens[0], ")")) {
                        throw new ParserError("parsing error");
                    }
                    tokens.shift();
                    return { type: 8 /* FunctionCall */, fn: left, args, kwargs };
                case "=":
                    if (left.type === 5 /* Name */) {
                        return {
                            type: 9 /* Assignment */,
                            name: left,
                            value: _parse(tokens, 10),
                        };
                    }
                case "[": {
                    // lookup in dictionary
                    const key = _parse(tokens);
                    if (!tokens[0] || !isSymbol(tokens[0], "]")) {
                        throw new ParserError("parsing error");
                    }
                    tokens.shift();
                    return {
                        type: 12 /* Lookup */,
                        target: left,
                        key: key,
                    };
                }
                case "if": {
                    const condition = _parse(tokens);
                    if (!tokens[0] || !isSymbol(tokens[0], "else")) {
                        throw new ParserError("parsing error");
                    }
                    tokens.shift();
                    const ifFalse = _parse(tokens);
                    return {
                        type: 13 /* If */,
                        condition,
                        ifTrue: left,
                        ifFalse,
                    };
                }
            }
    }
    throw new ParserError("Token cannot be parsed");
}

/**
 * @param {Token[]} tokens
 * @param {number} [bp]
 * @returns {AST}
 */
function _parse(tokens, bp = 0) {
    const token = tokens.shift();
    let expr = parsePrefix(token, tokens);
    while (tokens[0] && bindingPower(tokens[0]) > bp) {
        expr = parseInfix(expr, tokens.shift(), tokens);
    }
    return expr;
}

// -----------------------------------------------------------------------------
// Parse function
// -----------------------------------------------------------------------------

/**
 * Parse a list of tokens
 *
 * @param {Token[]} tokens
 * @returns {AST}
 */
export function parse(tokens) {
    if (tokens.length) {
        return _parse(tokens, 0);
    }
    throw new ParserError("Missing token");
}

/**
 * @param {any[]} args
 * @param {string[]} spec
 * @returns {{[name: string]: any}}
 */
export function parseArgs(args, spec) {
    const last = args[args.length - 1];
    const unnamedArgs = typeof last === "object" ? args.slice(0, -1) : args;
    const kwargs = typeof last === "object" ? last : {};
    for (let [index, val] of unnamedArgs.entries()) {
        kwargs[spec[index]] = val;
    }
    return kwargs;
}
