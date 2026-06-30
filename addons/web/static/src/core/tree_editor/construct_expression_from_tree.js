import { formatAST } from "@web/core/py_js/py";
import { isValidPath, not } from "./ast_utils";
import { Expression, astFromValue, isTree } from "./condition_tree";
import { COMPARATORS, TERM_OPERATORS_NEGATION } from "./operators";

function getNormalizedCondition(condition) {
    let { operator, negate } = condition;
    if (negate && typeof operator === "string" && TERM_OPERATORS_NEGATION[operator]) {
        operator = TERM_OPERATORS_NEGATION[operator];
        negate = false;
    }
    return { ...condition, operator, negate };
}

function isX2Many(ast, options) {
    if (isValidPath(ast, options)) {
        const fieldDef = options.getFieldDef(ast.value); // safe: isValidPath has not returned null;
        return ["many2many", "one2many"].includes(fieldDef.type);
    }
    return false;
}

function _constructExpressionFromTree(tree, options, isRoot = false) {
    if (tree.type === "connector" && tree.value === "|" && tree.children.length === 2) {
        // check if we have an "if else"
        const isSimpleAnd = (tree) =>
            tree.type === "connector" && tree.value === "&" && tree.children.length === 2;
        if (tree.children.every((c) => isSimpleAnd(c))) {
            const [c1, c2] = tree.children;
            for (let i = 0; i < 2; i++) {
                const c1Child = c1.children[i];
                const str1 = _constructExpressionFromTree({ ...c1Child }, options);
                for (let j = 0; j < 2; j++) {
                    const c2Child = c2.children[j];
                    const str2 = _constructExpressionFromTree(c2Child, options);
                    if (str1 === `not ${str2}` || `not ${str1}` === str2) {
                        /** @todo smth smarter. this is very fragile */
                        const others = [c1.children[1 - i], c2.children[1 - j]];
                        const str = _constructExpressionFromTree(c1Child, options);
                        const strs = others.map((c) => _constructExpressionFromTree(c, options));
                        return `${strs[0]} if ${str} else ${strs[1]}`;
                    }
                }
            }
        }
    }

    if (tree.type === "connector") {
        const connector = tree.value === "&" ? "and" : "or";
        const subExpressions = tree.children.map((c) => _constructExpressionFromTree(c, options));
        if (!subExpressions.length) {
            return connector === "and" ? "1" : "0";
        }
        let expression = subExpressions.join(` ${connector} `);
        if (!isRoot || tree.negate) {
            expression = `( ${expression} )`;
        }
        if (tree.negate) {
            expression = `not ${expression}`;
        }
        return expression;
    }

    if (tree.type === "complex_condition") {
        return tree.value;
    }

    tree = getNormalizedCondition(tree);
    const { path, operator, value } = tree;

    if (path instanceof Expression && operator === "=" && value === 1) {
        return path.toString();
    }

    const op = operator === "=" ? "==" : operator; // do something about is ?
    if (typeof op !== "string" || !COMPARATORS.includes(op)) {
        throw new Error("Invalid operator");
    }

    // we can assume that negate = false here: comparators have negation defined
    // and the tree has been normalized

    if ([0, 1].includes(path)) {
        if (operator !== "=" || value !== 1) {
            // check if this is too restricive for us
            return new Error("Invalid condition");
        }
        return formatAST({ type: 2, value: Boolean(path) });
    }

    const pathAST = astFromValue(path);
    if (typeof path == "string" && isValidPath({ type: 5, value: path }, options)) {
        pathAST.type = 5;
    }

    if (value === false && ["=", "!="].includes(operator)) {
        // true makes sense for non boolean fields?
        return formatAST(operator === "=" ? not(pathAST) : pathAST);
    }

    if (isTree(value)) {
        throw new Error("Invalid value");
    }

    let valueAST = astFromValue(value);
    if (
        ["in", "not in"].includes(operator) &&
        !(value instanceof Expression) &&
        ![4, 10].includes(valueAST.type)
    ) {
        valueAST = { type: 4, value: [valueAST] };
    }

    if (pathAST.type === 5 && isX2Many(pathAST, options) && ["in", "not in"].includes(operator)) {
        const ast = {
            type: 8,
            fn: {
                type: 15,
                obj: {
                    args: [pathAST],
                    type: 8,
                    fn: {
                        type: 5,
                        value: "set",
                    },
                },
                key: "intersection",
            },
            args: [valueAST],
        };
        return formatAST(operator === "not in" ? not(ast) : ast);
    }

    // add case true for boolean fields

    return formatAST({
        type: 7,
        op,
        left: pathAST,
        right: valueAST,
    });
}

export function constructExpressionFromTree(tree, options = {}) {
    return _constructExpressionFromTree(tree, options, true);
}
