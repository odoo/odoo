import { COMPARATORS, TERM_OPERATORS_NEGATION_EXTENDED } from "./operators";

export function isBool(ast) {
    return ast.type === 8 && ast.fn.type === 5 && ast.fn.value === "bool" && ast.args.length === 1;
}

export function isNot(ast) {
    return ast.type === 6 && ast.op === "not";
}

export function not(ast) {
    if (isNot(ast)) {
        return ast.right;
    }
    if (ast.type === 2) {
        return { ...ast, value: !ast.value };
    }
    if (ast.type === 7 && COMPARATORS.includes(ast.op)) {
        return { ...ast, op: TERM_OPERATORS_NEGATION_EXTENDED[ast.op] }; // do not use this if ast is within a domain context!
    }
    return { type: 6, op: "not", right: isBool(ast) ? ast.args[0] : ast };
}

export function isValidPath(ast, options) {
    const getFieldDef = options.getFieldDef || (() => null);
    if (ast.type === 5) {
        return getFieldDef(ast.value) !== null;
    }
    return false;
}
