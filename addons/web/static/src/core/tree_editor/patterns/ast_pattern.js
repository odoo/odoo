import { parseExpr } from "@web/core/py_js/py";
import { deepCopy } from "@web/core/utils/objects";
import { Hole, setHoleValues, upToHole } from "../hole";
import { Just, Nothing } from "../maybe_monad";
import { Pattern } from "./pattern";

const areEqualArraysOfASTs = upToHole((array, otherArray) => {
    if (array.length !== otherArray.length) {
        return false;
    }
    for (let i = 0; i < array.length; i++) {
        const elem = array[i];
        const otherElem = otherArray[i];
        if (!areEqualASTs(elem, otherElem)) {
            return false;
        }
    }
    return true;
});

const areEqualObjectsOfASTs = upToHole((object, otherObject) => {
    const keys = new Set(Object.keys(object));
    const otherKeys = new Set(Object.keys(otherObject));
    // @ts-ignore
    if (keys.symmetricDifference(otherKeys).size) {
        return false;
    }
    for (const key of keys) {
        const value = object[key];
        const otherValue = otherObject[key];
        if (!areEqualASTs(value, otherValue)) {
            return false;
        }
    }
    return true;
});

const areEqualValues = upToHole((value, otherValue) => value === otherValue);

const areEqualASTs = upToHole((ast, otherAST) => {
    if (ast.type !== otherAST.type) {
        return false;
    }
    switch (ast.type) {
        case 0 /** ASTNumber */:
        case 1 /** ASTString */:
        case 2 /** ASTBoolean */:
        case 5 /** ASTName */: {
            return areEqualValues(ast.value, otherAST.value);
        }
        case 3 /** ASTNone */:
            return true;
        case 4 /** ASTList */:
        case 10 /** ASTTuple */:
            return areEqualArraysOfASTs(ast.value, otherAST.value);
        case 6 /** ASTUnaryOperator */:
            return areEqualValues(ast.op, otherAST.op) && areEqualASTs(ast.right, otherAST.right);
        case 7 /** ASTBinaryOperator */:
        case 14 /** ASTBooleanOperator */:
            return (
                areEqualValues(ast.op, otherAST.op) &&
                areEqualASTs(ast.left, otherAST.left) &&
                areEqualASTs(ast.right, otherAST.right)
            );
        case 8 /** ASTFunctionCall */:
            return (
                areEqualASTs(ast.fn, otherAST.fn) &&
                areEqualArraysOfASTs(ast.args, otherAST.args) &&
                areEqualObjectsOfASTs(ast.kwargs, otherAST.kwargs)
            );
        case 9 /** ASTAssignment */:
            return areEqualASTs(ast.name, otherAST.name) && areEqualASTs(ast.value, otherAST.value);
        case 11 /** ASTDictionary */:
            return areEqualObjectsOfASTs(ast.value, otherAST.value);
        case 12 /** ASTLookup */:
            return areEqualASTs(ast.target, otherAST.target) && areEqualASTs(ast.key, otherAST.key);
        case 13 /** ASTIf */:
            return (
                areEqualASTs(ast.condition, otherAST.condition) &&
                areEqualASTs(ast.ifTrue, otherAST.ifTrue) &&
                areEqualASTs(ast.ifFalse, otherAST.ifFalse)
            );
        case 15 /** ASTObjLookup */:
            return areEqualValues(ast.key, otherAST.key) && areEqualASTs(ast.obj, otherAST.obj);
    }
});

function areEqualASTsUpToHole(ast, otherAST) {
    const { holeValues, unset } = setHoleValues();
    const equal = areEqualASTs(ast, otherAST);
    unset();
    return equal && holeValues;
}

const re = /(\w+)(\[(\d+)\])?/;
function writeAtLocation(struct, location, val) {
    // only support location of type "a.b[i].c...." but we don't need more here
    const parts = location.split(".").map((p) => {
        const [, key, , index] = re.exec(p);
        return [key, index && parseInt(index)];
    });
    let res = struct;
    for (let i = 0; i < parts.length - 1; i++) {
        const [key, index] = parts[i];
        res = res[key];
        if (index !== undefined) {
            res = res[index];
        }
    }
    const [key, index] = parts.at(-1);
    if (index !== undefined) {
        res[key][index] = val;
    } else {
        res[key] = val;
    }
}

export class ASTPattern extends Pattern {
    static of(ast, holeLocations = {}) {
        return new ASTPattern(ast, holeLocations);
    }
    constructor(ast, holeLocations = {}) {
        super();
        this._holeLocations = holeLocations;
        this._template = typeof ast === "string" ? parseExpr(ast) : ast;
        for (const [name, locations] of Object.entries(this._holeLocations)) {
            const val = new Hole(name);
            for (const location of locations) {
                writeAtLocation(this._template, location, val);
            }
        }
    }
    detect(ast) {
        ast = typeof ast === "string" ? parseExpr(ast) : ast;
        const holeValues = areEqualASTsUpToHole(this._template, ast);
        if (holeValues) {
            return Just.of(holeValues);
        }
        return Nothing.of();
    }
    make(holeValues) {
        const ast = deepCopy(this._template);
        for (const [name, locations] of Object.entries(this._holeLocations)) {
            const val = holeValues[name];
            for (const location of locations) {
                writeAtLocation(ast, location, val);
            }
        }
        return Just.of(ast);
    }
}
