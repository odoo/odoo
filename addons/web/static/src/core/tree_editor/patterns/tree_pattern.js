import { areEqualTrees, condition, Expression, operate } from "../condition_tree";
import { constructTreeFromDomain } from "../construct_tree_from_domain";
import { Hole, setHoleValues } from "../hole";
import { Just, Nothing } from "../maybe_monad";
import { Pattern } from "./pattern";

function areEqualTreesUpToHole(tree, otherTree) {
    const { holeValues, unset } = setHoleValues();
    const equal = areEqualTrees(tree, otherTree);
    unset();
    return equal && holeValues;
}

function replaceVariable(expr, values) {
    if (expr instanceof Expression && expr._ast.type === 5 && expr._ast.value in values) {
        return values[expr._ast.value];
    }
    return expr;
}

function replaceVariablesByValues(tree, values) {
    return operate((c) => {
        const { negate, path, operator, value } = c;
        return condition(
            replaceVariable(path, values),
            replaceVariable(operator, values),
            replaceVariable(value, values),
            negate
        );
    }, tree);
}

function replaceHole(expr, values) {
    if (expr instanceof Hole && expr.name in values) {
        return values[expr.name];
    }
    return expr;
}

function replaceHoleByValues(tree, values) {
    return operate((c) => {
        const { negate, path, operator, value } = c;
        return condition(
            replaceHole(path, values),
            replaceHole(operator, values),
            replaceHole(value, values),
            negate
        );
    }, tree);
}

export class TreePattern extends Pattern {
    static of(domain, vars) {
        return new TreePattern(domain, vars);
    }
    constructor(domain, vars) {
        super();
        const values = {};
        for (const name of vars) {
            values[name] = new Hole(name);
        }
        const tree = constructTreeFromDomain(domain);
        this._vars = vars;
        this._template = replaceVariablesByValues(tree, values);
    }
    detect(tree) {
        const holeValues = areEqualTreesUpToHole(this._template, tree);
        if (holeValues) {
            return Just.of({ ...holeValues });
        }
        return Nothing.of();
    }
    make(values) {
        for (const v of this._vars) {
            if (!(v in values)) {
                return Nothing.of();
            }
        }
        return Just.of(replaceHoleByValues(this._template, values));
    }
}
