import { bp } from "./py_parser";
import { PyDate, PyDateTime } from "./py_date";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef { import("./py_parser").AST } AST
 */

// -----------------------------------------------------------------------------
// Utils
// -----------------------------------------------------------------------------

/**
 * Represent any value as a primitive AST
 *
 * @param {any} value
 * @returns {AST}
 */
export function toPyValue(value) {
    switch (typeof value) {
        case "string":
            return { type: 1 /* String */, value };
        case "number":
            return { type: 0 /* Number */, value };
        case "boolean":
            return { type: 2 /* Boolean */, value };
        case "object":
            if (Array.isArray(value)) {
                return { type: 4 /* List */, value: value.map(toPyValue) };
            } else if (value === null) {
                return { type: 3 /* None */ };
            } else if (value instanceof Date) {
                return { type: 1, value: PyDateTime.convertDate(value) };
            } else if (value instanceof PyDate || value instanceof PyDateTime) {
                return { type: 1, value };
            } else {
                const content = {};
                for (const key in value) {
                    content[key] = toPyValue(value[key]);
                }
                return { type: 11 /* Dictionary */, value: content };
            }
        default:
            throw new Error("Invalid type");
    }
}

/**
 * @param {AST} ast
 * @param {number} [lbp] left binding power
 * @return {string}
 */
export function formatAST(ast, lbp = 0) {
    switch (ast.type) {
        case 3 /* None */:
            return "None";
        case 1 /* String */:
            return JSON.stringify(ast.value);
        case 0 /* Number */:
            return String(ast.value);
        case 2 /* Boolean */:
            return ast.value ? "True" : "False";
        case 4 /* List */:
            return `[${ast.value.map(formatAST).join(", ")}]`;
        case 6 /* UnaryOperator */:
            if (ast.op === "not") {
                return `not ` + formatAST(ast.right, 50);
            }
            return ast.op + formatAST(ast.right, 130);
        case 7 /* BinaryOperator */: {
            const abp = bp(ast.op);
            const str = `${formatAST(ast.left, abp)} ${ast.op} ${formatAST(ast.right, abp)}`;
            return abp < lbp ? `(${str})` : str;
        }
        case 11 /* Dictionary */: {
            const pairs = [];
            for (const k in ast.value) {
                pairs.push(`"${k}": ${formatAST(ast.value[k])}`);
            }
            return `{` + pairs.join(", ") + `}`;
        }
        case 10 /* Tuple */:
            return `(${ast.value.map(formatAST).join(", ")})`;
        case 5 /* Name */:
            return ast.value;
        case 12 /* Lookup */: {
            return `${formatAST(ast.target)}[${formatAST(ast.key)}]`;
        }
        case 13 /* If */: {
            const { ifTrue, condition, ifFalse } = ast;
            return `${formatAST(ifTrue)} if ${formatAST(condition)} else ${formatAST(ifFalse)}`;
        }
        case 14 /* BooleanOperator */: {
            const abp = bp(ast.op);
            const str = `${formatAST(ast.left, abp)} ${ast.op} ${formatAST(ast.right, abp)}`;
            return abp < lbp ? `(${str})` : str;
        }
        case 15 /* ObjLookup */:
            return `${formatAST(ast.obj, 150)}.${ast.key}`;
        case 8 /* FunctionCall */: {
            const args = ast.args.map(formatAST);
            const kwargs = [];
            for (const kwarg in ast.kwargs) {
                kwargs.push(`${kwarg} = ${formatAST(ast.kwargs[kwarg])}`);
            }
            const argStr = args.concat(kwargs).join(", ");
            return `${formatAST(ast.fn)}(${argStr})`;
        }
    }
    throw new Error("invalid expression: " + ast);
}

export const PY_DICT = Object.create(null);

/**
 * @param {Object} obj
 * @returns {AST} a python dictionary
 */
export function toPyDict(obj) {
    return new Proxy(obj, {
        getPrototypeOf() {
            return PY_DICT;
        },
    });
}
