import { Domain } from "@web/core/domain";
import { parseDate, serializeDate } from "@web/core/l10n/dates";
import { parseTime } from "@web/core/l10n/time";
import { formatAST, parseExpr } from "@web/core/py_js/py";
import { toPyValue } from "@web/core/py_js/py_utils";
import { ASTPattern } from "@web/core/tree_editor/ast_pattern";
import { setHoleValues, upToHole } from "@web/core/tree_editor/hole";
import { Just, Nothing } from "@web/core/tree_editor/maybe_monad";
import { _Pattern, Pattern } from "@web/core/tree_editor/pattern";
import { useService } from "@web/core/utils/hooks";
import { isObject, omit, pick } from "@web/core/utils/objects";

const { DateTime } = luxon;

// /** @typedef { import("@web/core/py_js/py_parser").AST } AST */
/** @typedef { import("@web/core/py_js/py_parser").ASTList } ASTList */
/** @typedef {import("@web/core/domain").DomainRepr} DomainRepr */

/**
 * @typedef {number|string|boolean|Expression} Atom
 */

/**
 * @typedef {Object} Options
 * @property {(value: Value | Couple) => (null|Object)} [getFieldDef]
 * @property {boolean} [distributeNot]
 */

/**
 * @param {Value|ConditionTree} value
 * @returns  {import("@web/core/py_js/py_parser").AST}
 */
export function toAST(value) {
    if (value instanceof ConditionTree) {
        return value.toAST();
    }
    if (Array.isArray(value)) {
        return { type: 4, value: value.map(toAST) };
    }
    return toPyValue(value);
}

function isNotConnector(ast) {
    return ast.type === 1 && ast.value === "!";
}

export const MAPPING_AST_TYPE_CONSTRUCTOR = {};

export class AST {
    static of(ast) {
        ast = typeof ast === "string" ? parseExpr(ast) : ast;
        const CONSTRUCTOR = MAPPING_AST_TYPE_CONSTRUCTOR[ast.type];
        return new CONSTRUCTOR(ast);
    }
    constructor(ast) {
        ast = typeof ast === "string" ? parseExpr(ast) : ast;
        this._ast = ast;
        this._string = formatAST(ast);
    }
}

export class NumberAST extends AST {
    constructor(ast) {
        super(ast);
        this.value = this._ast.value;
    }
}
MAPPING_AST_TYPE_CONSTRUCTOR[0] = NumberAST;

export function useConditionTreeProcessor(configuration = {}) {
    const services = configuration.services || {};
    const fieldService = services.fieldService || useService("field");
    const nameService = services.nameService || useService("name");
    return new ConditionTreeProcessor(fieldService, nameService);
}

export class ConditionTreeProcessor {
    static operations = [];
    constructor(fieldService, nameService) {
        this.fieldService = fieldService;
        this.nameService = nameService;
    }
    buildTreeFromDomain(domain) {
        const options = {};
        return ConditionTree.fromDomain(domain, options);
    }
}

export class ConditionTree {
    type = "none";
    /**
     * @param {DomainRepr} domain
     * @param {Object} [options={}] see construcTree API
     * @returns {ConditionTree} a (simple) tree representation of a domain
     */
    static fromDomain(domain, options = {}) {
        domain = new Domain(domain);
        const domainAST = domain.ast;
        const initialASTs = domainAST.value;
        if (!initialASTs.length) {
            return Connector.of("&");
        }
        const { tree } = this._construcTree(initialASTs, options);
        return tree;
    }
    /**
     * @param {AST[]} ASTs
     * @param {Options} [options={}]
     * @param {boolean} [negate=false]
     * @returns {{ tree: ConditionTree, remaimingASTs: AST[] }}
     */
    static _construcTree(ASTs, options = {}, negate = false) {
        const [firstAST, ...tailASTs] = ASTs;

        if (isNotConnector(firstAST)) {
            return this._construcTree(tailASTs, options, !negate);
        }

        const type = firstAST.type === 1 ? "connector" : "condition";

        if (type === "condition") {
            const [pathAST, operatorAST, valueAST] = firstAST.value;
            const path = toValue(pathAST);
            const operator = toValue(operatorAST);
            /** @type Value|ConditionTree */
            let value = toValue(valueAST);
            if (typeof operator === "string" && ["any", "not any"].includes(operator)) {
                try {
                    value = this.fromDomain(formatAST(valueAST), {
                        ...options,
                        getFieldDef: (p) => options.getFieldDef?.(new Couple(path, p)) || null,
                    });
                } catch {
                    value = Array.isArray(value) ? value : [value];
                }
            }
            const tree = Condition.of(path, operator, value, negate);
            normalizeCondition(tree);
            return { tree, remaimingASTs: tailASTs };
        }

        let value = firstAST.value;
        if (options.distributeNot && negate) {
            value = value === "&" ? "|" : "&";
            negate = false;
        }

        const tree = Connector.of(value, [], negate);

        let remaimingASTs = tailASTs;
        for (let i = 0; i < 2; i++) {
            const { tree: child, remaimingASTs: otherASTs } = this._construcTree(
                remaimingASTs,
                options,
                options.distributeNot && negate
            );
            remaimingASTs = otherASTs;
            addChild(tree, child);
        }

        return { tree, remaimingASTs };
    }

    /**
     * @returns {AST}
     */
    toAST() {
        return { type: 3 };
    }
    /**
     * @returns {string}
     */
    toString() {
        return formatAST(this.toAST());
    }
}

export class Expression extends ConditionTree {
    type = "complex_condition";
    static of(ast) {
        return new Expression(ast);
    }
    constructor(ast) {
        super();
        this._ast = typeof ast === "string" ? parseExpr(ast) : ast;
        this._expr = formatAST(ast);
    }
    toAST() {
        return this._ast;
    }
    toString() {
        return this._expr;
    }
}

export class Connector extends ConditionTree {
    type = "connector";
    static of(value, children, negate) {
        return new Connector(value, children, negate);
    }
    /**
     * @param {"&"|"|"} value
     * @param {ConditionTree[]} children
     * @param {boolean} [negate=false]
     */
    constructor(value, children = [], negate = false) {
        super();
        this.value = value;
        this.children = children;
        this.negate = negate;
    }
    /**
     * @returns {AST}
     */
    domainAST() {
        return { type: 4, value: this.getASTs() };
    }
    getASTs() {
        const ASTs = [];
        const length = this.children.length;
        if (length && this.negate) {
            ASTs.push(toAST("!"));
        }
        for (let i = 0; i < length - 1; i++) {
            ASTs.push(toAST(this.value));
        }
        for (const child of this.children) {
            // @ts-ignore
            ASTs.push(...child.getASTs());
        }
        return ASTs;
    }
    /**
     * @returns {string}
     */
    toDomainRepr() {
        return formatAST(this.domainAST());
    }
}

export class Condition extends ConditionTree {
    type = "condition";
    static of(path, operator, value, negate = false) {
        return new Condition(path, operator, value, negate);
    }
    /**
     * @param {Value} path
     * @param {Value} operator
     * @param {Value|ConditionTree} value
     * @param {boolean} [negate=false]
     */
    constructor(path, operator, value, negate = false) {
        super();
        this.path = path;
        this.operator = operator;
        this.value = value;
        this.negate = negate;
    }
    /**
     * @returns {AST}
     */
    domainAST() {
        return { type: 4, value: this.getASTs() };
    }
    getASTs() {
        /** @type AST[] */
        const ASTs = [];
        if (this.negate) {
            ASTs.push(toAST("!"));
        }
        ASTs.push({
            type: 10,
            value: [this.path, this.operator, this.value].map(toAST),
        });
        return ASTs;
    }
    /**
     * @returns {string}
     */
    toDomainRepr() {
        return formatAST(this.domainAST());
    }
}

export class Value {
    static of(value) {
        return new Value(value);
    }
    constructor(value) {
        if (!["number", "string", "boolean"].includes(typeof value)) {
            throw new Error("Unexpected value type");
        }
        this.value = value;
    }
    clone() {
        return Value.of(this.value);
    }
}

export class Hole extends ConditionTree {
    static of(name) {
        return new Hole(name);
    }
    /**
     * @param {string} name
     */
    constructor(name) {
        super();
        this.name = name;
    }
}

export const TERM_OPERATORS_NEGATION = {
    "<": ">=",
    ">": "<=",
    "<=": ">",
    ">=": "<",
    "=": "!=",
    "!=": "=",
    in: "not in",
    like: "not like",
    ilike: "not ilike",
    "not in": "in",
    "not like": "like",
    "not ilike": "ilike",
};

export class Couple {
    constructor(x, y) {
        this.fst = x;
        this.snd = y;
    }
}

const areEqualValues = upToHole(
    (value, otherValue) => formatValue(value) === formatValue(otherValue)
);

const areEqualArraysOfTrees = upToHole((array, otherArray) => {
    if (array.length !== otherArray.length) {
        return false;
    }
    for (let i = 0; i < array.length; i++) {
        const elem = array[i];
        const otherElem = otherArray[i];
        if (!areEqualTrees(elem, otherElem)) {
            return false;
        }
    }
    return true;
});

const areEqualTrees = upToHole((tree, otherTree) => {
    if (tree.type !== otherTree.type) {
        return false;
    }
    if (tree.negate !== otherTree.negate) {
        return false;
    }
    if (tree.type === "condition") {
        if (!areEqualValues(tree.path, otherTree.path)) {
            return false;
        }
        if (!areEqualValues(tree.operator, otherTree.operator)) {
            return false;
        }
        if (isTree(tree.value)) {
            if (isTree(otherTree.value)) {
                return areEqualTrees(tree.value, otherTree.value);
            }
            return false;
        } else if (isTree(otherTree.value)) {
            return false;
        }
        if (!areEqualValues(tree.value, otherTree.value)) {
            return false;
        }
        return true;
    }
    if (!areEqualValues(tree.value, otherTree.value)) {
        return false;
    }
    if (tree.type === "complex_condition") {
        return true;
    }
    return areEqualArraysOfTrees(tree.children, otherTree.children);
});

function areEqualTreesUpToHole(tree, otherTree) {
    const { holeValues, unset } = setHoleValues();
    const equal = areEqualTrees(tree, otherTree);
    unset();
    return equal && holeValues;
}

export function areEquivalentTrees(tree, otherTree) {
    const simplifiedTree = applyTransformations(FULL_VIRTUAL_OPERATORS_DESTRUCTION, tree);
    const otherSimplifiedTree = applyTransformations(FULL_VIRTUAL_OPERATORS_DESTRUCTION, otherTree);
    return areEqualTrees(simplifiedTree, otherSimplifiedTree);
}

export function formatValue(value) {
    return formatAST(toAST(value));
}

export function normalizeValue(value) {
    return toValue(toAST(value)); // no array in array (see isWithinArray)
}

/**
 * @param {import("@web/core/py_js/py_parser").AST} ast
 * @returns {Value}
 */
export function toValue(ast, isWithinArray = false) {
    if ([4, 10].includes(ast.type) && !isWithinArray) {
        /** 4: list, 10: tuple */
        return ast.value.map((v) => toValue(v, true));
    } else if ([0, 1, 2].includes(ast.type)) {
        /** 0: number, 1: string, 2: boolean */
        return ast.value;
    } else if (ast.type === 6 && ast.op === "-" && ast.right.type === 0) {
        /** 6: unary operator */
        return -ast.right.value;
    } else if (ast.type === 5 && ["false", "true"].includes(ast.value)) {
        /** 5: name */
        return JSON.parse(ast.value);
    } else {
        return new Expression(ast);
    }
}

export function isTree(value) {
    return (
        typeof value === "object" &&
        !(value instanceof Domain) &&
        !(value instanceof Expression) &&
        !(value instanceof Hole) &&
        !Array.isArray(value) &&
        value !== null
    );
}

/**
 * @param {Connector} parent
 * @param {ConditionTree} child
 */
export function addChild(parent, child) {
    if (child.type === "connector" && !child.negate && child.value === parent.value) {
        parent.children.push(...child.children);
    } else {
        parent.children.push(child);
    }
}

/**
 * @param {Condition} condition
 * @returns {Condition}
 */
export function getNormalizedCondition(condition) {
    let { operator, negate } = condition;
    if (negate && typeof operator === "string" && TERM_OPERATORS_NEGATION[operator]) {
        operator = TERM_OPERATORS_NEGATION[operator];
        negate = false;
    }
    return { ...condition, operator, negate };
}

export function normalizeCondition(condition) {
    Object.assign(condition, getNormalizedCondition(condition));
}

////////////////////////////////////////////////////////////////////////////////
// some helpers
////////////////////////////////////////////////////////////////////////////////

function getFieldType(path, options) {
    return options.getFieldDef?.(path)?.type;
}

export function splitPath(path) {
    const pathParts = typeof path === "string" ? path.split(".") : [];
    const lastPart = pathParts.pop() || "";
    const initialPath = pathParts.join(".");
    return { initialPath, lastPart };
}

function allEqual(...values) {
    return values.slice(1).every((v) => v === values[0]);
}

export function applyTransformations(transformations, transformed, ...fixedParams) {
    for (let i = transformations.length - 1; i >= 0; i--) {
        const fn = transformations[i];
        transformed = fn(transformed, ...fixedParams);
    }
    return transformed;
}

function rewriteNConsecutiveChildren(transformation, connector, options = {}, N = 2) {
    const children = [];
    const currentChildren = connector.children;
    for (let i = 0; i < currentChildren.length; i++) {
        const NconsecutiveChildren = currentChildren.slice(i, i + N);
        let replacement = null;
        if (NconsecutiveChildren.length === N) {
            replacement = transformation(connector, NconsecutiveChildren, options);
        }
        if (replacement) {
            children.push(replacement);
            i += N - 1;
        } else {
            children.push(NconsecutiveChildren[0]);
        }
    }
    return { ...connector, children };
}

export function normalizeConnector(connector) {
    const newTree = { ...connector, children: [] };
    for (const child of connector.children) {
        addChild(newTree, child);
    }
    if (newTree.children.length === 1) {
        const child = newTree.children[0];
        if (newTree.negate) {
            const newChild = { ...child, negate: !child.negate };
            if (newChild.type === "condition") {
                return getNormalizedCondition(newChild);
            }
            return newChild;
        }
        return child;
    }
    return newTree;
}

class Operation {
    operate(value) {
        return value;
    }
}

class OperationOnConditionTree extends Operation {
    operate(value) {
        if (value instanceof Connector) {
            return this.operateOnConnector(value, {
                value: this.operate(value.value),
                children: this.operate(value.children),
                negate: this.operate(value.negate),
            });
        }
        if (value instanceof Condition) {
            return this.operateOnCondition(value, {
                path: this.operate(value.path),
                operator: this.operate(value.operator),
                value: this.operate(value.value),
                negate: this.operate(value.negate),
            });
        }
        if (value instanceof Expression) {
            return this.operateOnExpression(value, {
                _ast: this.operate(value._ast),
            });
        }
        if (value instanceof Array) {
            return this.operateOnArray(value.map((v) => this.operate(v)));
        }
        if (["number", "string", "boolean"].includes(typeof value)) {
            return this.operateOnValue(value);
        }
        if (isObject(value)) {
            //ast
            return value;
        }

        throw new Error("Not implemented");
    }
    operateOnConnector(connector, { value, children, negate }) {
        return connector;
    }
    operateOnCondition(condition, { path, operator, value, negate }) {
        return condition;
    }
    operateOnExpression(expression, { _ast }) {
        return expression;
    }
    operateOnArray(array, values) {
        return array;
    }
    operateOnHole(hole) {
        return hole;
    }
    operateOnValue(value) {
        return value;
    }
}

class CloneOperation extends OperationOnConditionTree {
    static of() {
        return new CloneOperation();
    }
    operateOnConnector(connector, { value, children, negate }) {
        return Connector.of(value, children, negate);
    }
    operateOnCondition(condition, { path, operator, value, negate }) {
        return Condition.of(path, operator, value, negate);
    }
    operateOnExpression(expression, { _ast }) {
        return Expression.of(_ast);
    }
    operateOnArray(array, values) {
        return values;
    }
    operateOnHole(hole) {
        return Hole.of(hole.name);
    }
    operateOnValue(value) {
        return value;
    }
}

const cloneOp = CloneOperation.of();
/**
 * @param {ConditionTree} tree
 * @returns {ConditionTree}
 */
export function cloneTree(tree) {
    return cloneOp.operate(tree);
}

class TargetedOperation extends CloneOperation {
    static of() {
        return new TargetedOperation(...arguments);
    }
    constructor({
        operateOnConnector,
        operateOnCondition,
        operateOnExpression,
        operateOnArray,
        operateOnHole,
        operateOnValue,
    }) {
        super();
        this._operateOnConnector = operateOnConnector;
        this._operateOnCondition = operateOnCondition;
        this._operateOnExpression = operateOnExpression;
        this._operateOnArray = operateOnArray;
        this._operateOnHole = operateOnHole;
        this._operateOnValue = operateOnValue;
    }
    operateOnConnector() {
        return this._operateOnConnector
            ? this._operateOnConnector(...arguments)
            : super.operateOnConnector(...arguments);
    }
    operateOnCondition() {
        return this._operateOnCondition
            ? this._operateOnCondition(...arguments)
            : super.operateOnCondition(...arguments);
    }
    operateOnExpression() {
        return this._operateOnExpression
            ? this._operateOnExpression(...arguments)
            : super.operateOnExpression(...arguments);
    }
    operateOnArray() {
        return this._operateOnArray
            ? this._operateOnArray(...arguments)
            : super.operateOnArray(...arguments);
    }
    operateOnHole() {
        return this._operateOnHole
            ? this._operateOnHole(...arguments)
            : super.operateOnHole(...arguments);
    }
    operateOnValue() {
        return this._operateOnValue
            ? this._operateOnValue(...arguments)
            : super.operateOnValue(...arguments);
    }
}

class TreePattern extends Pattern {
    static of(domain, vars) {
        return new TreePattern(domain, vars);
    }
    constructor(domain, vars) {
        super();
        const values = {};
        for (const name of vars) {
            values[name] = new Hole(name);
        }
        const tree = ConditionTree.fromDomain(domain);
        // @ts-ignore
        const replaceVariablesByValuesOp = new TargetedOperation({
            operateOnExpression: (expression, { _ast }) => {
                if (_ast.type === 5 && _ast.value in values) {
                    return values[_ast.value];
                }
                return expression;
            },
        });
        this._template = replaceVariablesByValuesOp.operate(tree);
    }
    detect(tree) {
        const holeValues = areEqualTreesUpToHole(this._template, tree);
        if (holeValues) {
            return Just.of({ ...holeValues });
        }
        return Nothing.of();
    }
    make(values) {
        // @ts-ignore
        const replaceHoleByValuesOp = new TargetedOperation({
            operateOnHole: (hole) => {
                if (hole.name in values) {
                    return values[hole.name];
                }
            },
        });
        return Just.of(replaceHoleByValuesOp.operate(this._template));
    }
}

////////////////////////////////////////////////////////////////////////////////
// between - is_not_between
////////////////////////////////////////////////////////////////////////////////

/**
 * @param {Connector} c
 * @param {[Condition, Condition]} param
 */
function _createBetweenOperator(c, [child1, child2]) {
    if (!allEqual("condition", child1.type, child2.type)) {
        return;
    }
    if (formatValue(child1.path) !== formatValue(child2.path)) {
        return;
    }
    if (c.value === "&" && child1.operator === ">=" && child2.operator === "<=") {
        return Condition.of(child1.path, "between", normalizeValue([child1.value, child2.value]));
    }
    if (c.value === "|" && child1.operator === "<" && child2.operator === ">") {
        return Condition.of(
            child1.path,
            "is_not_between",
            normalizeValue([child1.value, child2.value])
        );
    }
}

/**
 * @param {Condition} c
 */
function _removeBetweenOperator(c) {
    const { negate, path, operator, value } = c;
    if (!Array.isArray(value)) {
        return;
    }
    if (operator === "between") {
        return Connector.of(
            "&",
            [Condition.of(path, ">=", value[0]), Condition.of(path, "<=", value[1])],
            negate
        );
    } else if (operator === "is_not_between") {
        return Connector.of(
            "|",
            [Condition.of(path, "<", value[0]), Condition.of(path, ">", value[1])],
            negate
        );
    }
}

////////////////////////////////////////////////////////////////////////////////
// special paths
////////////////////////////////////////////////////////////////////////////////

/**
 * @param {Condition} c
 * @param {Options} [options={}]
 */
function _createSpecialPath(c, options = {}) {
    const { negate, path, operator, value } = c;
    const { initialPath, lastPart } = splitPath(path);
    const { lastPart: previousPart } = splitPath(initialPath);
    if (!["__date", "__time", ""].includes(previousPart) && lastPart) {
        if (getFieldType(initialPath, options) === "datetime") {
            const pathFieldType = getFieldType(path, options);
            if (pathFieldType === "date_option") {
                const newPath = [initialPath, "__date", lastPart].join(".");
                return Condition.of(newPath, operator, value, negate);
            }
            if (pathFieldType === "time_option") {
                const newPath = [initialPath, "__time", lastPart].join(".");
                return Condition.of(newPath, operator, value, negate);
            }
        }
    }
}

/**
 * @param {Condition} c
 */
function _removeSpecialPath(c) {
    const { negate, path, operator, value } = c;
    const { initialPath, lastPart } = splitPath(path);
    const { initialPath: subPath, lastPart: previousPart } = splitPath(initialPath);
    if (["__date", "__time"].includes(previousPart) && lastPart) {
        return Condition.of([subPath, lastPart].join("."), operator, value, negate);
    }
}

////////////////////////////////////////////////////////////////////////////////
// __time - __date
////////////////////////////////////////////////////////////////////////////////

function parseDateCustom(value) {
    try {
        return parseDate(value);
    } catch {
        return null;
    }
}

function to2Digit(nat) {
    return nat < 10 ? `0${nat}` : `${nat}`;
}

class ParamsPattern extends Pattern {
    constructor(options = {}) {
        super();
        this.options = options;
    }
    detect({ path1, path2, path3, operator, value1, value2, value3 }) {
        const { initialPath: ip1, lastPart: lp1 } = splitPath(path1);
        const { initialPath: ip2, lastPart: lp2 } = splitPath(path2);
        const { initialPath: ip3, lastPart: lp3 } = splitPath(path3);
        if (
            !allEqual(ip1, ip2, ip3) ||
            ip1 === "" ||
            getFieldType(ip1, this.options) !== "datetime"
        ) {
            return Nothing.of();
        }
        let lastPart;
        if (lp1 === "year_number" && lp2 === "month_number" && lp3 === "day_of_month") {
            lastPart = "__date";
        }
        if (lp1 === "hour_number" && lp2 === "minute_number" && lp3 === "second_number") {
            lastPart = "__time";
        }

        if (!lastPart) {
            return Nothing.of();
        }

        const path = `${ip1}.${lastPart}`;

        let value;
        let success = false;
        if (allEqual(false, value1, value2, value3) && ["=", "!="].includes(operator)) {
            return Just.of(Condition.of(path, operator, false));
        }

        if ([value1, value2, value3].some((v) => !Number.isInteger(v) || v < 0)) {
            return Nothing.of();
        }

        if (lastPart === "__date") {
            const date = parseDateCustom(`${value1}-${to2Digit(value2)}-${to2Digit(value3)}`);
            if (date) {
                success = true;
                value = serializeDate(date);
            }
        } else {
            const time = parseTime(
                `${to2Digit(value1)}:${to2Digit(value2)}:${to2Digit(value3)}`,
                true
            );
            if (time) {
                success = true;
                value = DateTime.fromObject(pick(time, "hour", "minute", "second")).toFormat(
                    "HH:mm:ss"
                );
            }
        }

        if (success) {
            return Just.of(Condition.of(path, operator, value));
        }
        return Nothing.of();
    }
    make(c) {
        const { path, operator, value } = c;
        const { initialPath, lastPart } = splitPath(path);
        if (!initialPath || !["__date", "__time"].includes(lastPart)) {
            return Nothing.of();
        }
        let path1;
        let path2;
        let path3;
        let value1;
        let value2;
        let value3;
        if (lastPart === "__date") {
            path1 = `${initialPath}.year_number`;
            path2 = `${initialPath}.month_number`;
            path3 = `${initialPath}.day_of_month`;
        } else {
            path1 = `${initialPath}.hour_number`;
            path2 = `${initialPath}.minute_number`;
            path3 = `${initialPath}.second_number`;
        }

        let success = false;
        if (value === false) {
            success = true;
            value1 = false;
            value2 = false;
            value3 = false;
        } else if (lastPart === "__date") {
            const date = typeof value === "string" ? parseDateCustom(value) : null;
            if (date) {
                success = true;
                value1 = date.year;
                value2 = date.month;
                value3 = date.day;
            }
        } else {
            const time = typeof value === "string" ? parseTime(value, true) : null;
            if (time) {
                success = true;
                value1 = time.hour;
                value2 = time.minute;
                value3 = time.second;
            }
        }

        if (success) {
            return Just.of({
                path1,
                path2,
                path3,
                operator,
                value1,
                value2,
                value3,
            });
        }
        return Nothing.of();
    }
}

const addRemoveOperatorP = (operator) =>
    _Pattern.of(
        (values) => Just.of({ ...values, operator }),
        (values) => {
            if (values.operator !== operator) {
                return Nothing.of();
            }
            return Just.of(omit(values, "operator"));
        }
    );

const VARS = ["path1", "path2", "path3", "value1", "value2", "value3"];
const makePattern = (operator) =>
    Pattern.C([
        TreePattern.of(
            `[
                "|",
                "|",
                    (path1, "${operator}", value1),
                    "&",
                        (path1, "=", value1),
                        (path2, "${operator}", value2),
                    "&",
                    "&",
                        (path1, "=", value1),
                        (path2, "=", value2),
                        (path3, "${operator}", value3),
            ]`,
            VARS
        ),
        addRemoveOperatorP(operator),
    ]);

const greaterOpP = makePattern(">");
const greaterOrEqualOpP = makePattern(">=");
const leaserOpP = makePattern("<");
const leaserOrEqualOpP = makePattern("<=");

const equalOpP = Pattern.C([
    TreePattern.of(
        `["&", "&", (path1, "=", value1), (path2, "=", value2), (path3, "=", value3)]`,
        VARS
    ),
    addRemoveOperatorP("="),
]);

const inequalOpP = Pattern.C([
    TreePattern.of(
        `[ "|", "|", (path1, "!=", value1), (path2, "!=", value2), (path3, "!=", value3)]`,
        VARS
    ),
    addRemoveOperatorP("!="),
]);

const operatorPatterns = [
    greaterOpP,
    greaterOrEqualOpP,
    leaserOpP,
    leaserOrEqualOpP,
    equalOpP,
    inequalOpP,
];

/**
 * @param {Connector} c
 * @param {[Condition, Condition, Condition]} param
 * @param {Options} [options={}]
 */
function _createDatetimeOption(c, [child1, child2, child3], options = {}) {
    const paramsPattern = new ParamsPattern(options);
    const pattern = Pattern.C([Pattern.S(operatorPatterns), paramsPattern]);
    const mv = pattern.detect(Connector.of(c.value, [child1, child2, child3]));
    if (mv instanceof Nothing) {
        return;
    }
    return mv.value;
}

/**
 * @param {Condition} c
 */
function _removeDatetimeOption(c) {
    const paramsPattern = new ParamsPattern();
    const pattern = Pattern.C([Pattern.S(operatorPatterns), paramsPattern]);
    const mv = pattern.make(c);
    if (mv instanceof Nothing) {
        return;
    }
    return mv.value;
}

/////////////////////////////////////////////////////////////////////////////////
// set - not_set - starts_with - ends_with - next - not_next - last - not_last
// today - not_today
/////////////////////////////////////////////////////////////////////////////////

export const DATETIME_TODAY_STRING_EXPRESSION = `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`;
export const DATETIME_END_OF_TODAY_STRING_EXPRESSION = `datetime.datetime.combine(context_today(), datetime.time(23, 59, 59)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`;
export const DATE_TODAY_STRING_EXPRESSION = `context_today().strftime("%Y-%m-%d")`;

export function isTodayExpr(val, type) {
    return type === "date"
        ? val._expr === DATE_TODAY_STRING_EXPRESSION
        : val._expr === DATETIME_TODAY_STRING_EXPRESSION;
}

export function isEndOfTodayExpr(val) {
    return val._expr === DATETIME_END_OF_TODAY_STRING_EXPRESSION;
}

const DELTA_DATE_PATTERN = ASTPattern.of(
    `(context_today() + relativedelta(period=amount)).strftime('%Y-%m-%d')`,
    {
        kwargs: ["fn.obj.right.kwargs"], // target in ast the kwargs with period=amount
    }
);

const DELTA_DATETIME_PATTERN = ASTPattern.of(
    `datetime.datetime.combine(context_today() + relativedelta(period=amount), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
    {
        kwargs: ["fn.obj.fn.obj.args[0].right.kwargs"], // target in ast the kwargs with period=amount
    }
);

function getProcessedDelta(expr, type) {
    if (!(expr instanceof Expression)) {
        return Nothing.of();
    }
    const ast = expr._ast;
    const mv =
        type === "date" ? DELTA_DATE_PATTERN.detect(ast) : DELTA_DATETIME_PATTERN.detect(ast);
    if (mv instanceof Nothing) {
        return null;
    }
    const { kwargs } = mv.value;
    if (Object.keys(kwargs).length !== 1) {
        return null;
    }
    const [option, amountAST] = Object.entries(kwargs)[0];
    return [toValue(amountAST), option];
}

function getDeltaExpression(val, type) {
    const [amount, option] = val;
    const values = { kwargs: { [option]: toAST(amount) } };
    const mv =
        type === "date" ? DELTA_DATE_PATTERN.make(values) : DELTA_DATETIME_PATTERN.make(values);
    if (mv instanceof Nothing) {
        return null;
    }
    const ast = mv.value;
    return Expression.of(ast);
}

/**
 * @param {Condition} c
 * @param {Options} [options={}]
 */
function _createVirtualOperator(c, options = {}) {
    const { negate, path, operator, value } = c;
    const fieldType = getFieldType(path, options);
    if (typeof operator === "string" && ["=", "!="].includes(operator)) {
        if (fieldType) {
            if (fieldType === "boolean" && value === true) {
                return Condition.of(path, operator === "=" ? "set" : "not_set", value, negate);
            } else if (!["many2one", "date", "datetime"].includes(fieldType) && value === false) {
                return Condition.of(path, operator === "=" ? "not_set" : "set", value, negate);
            }
        }
    }
    if (typeof value === "string" && operator === "=ilike") {
        if (value.endsWith("%")) {
            return Condition.of(path, "starts_with", value.slice(0, -1), negate);
        }
        if (value.startsWith("%")) {
            return Condition.of(path, "ends_with", value.slice(1), negate);
        }
    }
    if (
        ["between", "is_not_between"].includes(operator) &&
        ["date", "datetime"].includes(fieldType)
    ) {
        let delta;
        let virtualOperator;
        if (isTodayExpr(value[0], fieldType)) {
            delta = getProcessedDelta(value[1], fieldType);
            virtualOperator = operator === "between" ? "next" : "not_next";
        } else if (isTodayExpr(value[1], fieldType)) {
            delta = getProcessedDelta(value[0], fieldType);
            if (delta) {
                delta[0] = Number.isInteger(delta[0]) ? -delta[0] : delta[0];
            }
            virtualOperator = operator === "between" ? "last" : "not_last";
        }
        if (delta) {
            return Condition.of(path, virtualOperator, [...delta, fieldType], negate);
        }
    }
    if (fieldType === "date" && ["=", "!="].includes(operator) && isTodayExpr(value, fieldType)) {
        return Condition.of(path, operator === "=" ? "today" : "not_today", value, negate);
    }
    if (
        fieldType === "datetime" &&
        ["between", "is_not_between"].includes(operator) &&
        isTodayExpr(value[0], fieldType) &&
        isEndOfTodayExpr(value[1])
    ) {
        return Condition.of(path, operator === "between" ? "today" : "not_today", value, negate);
    }
}

/**
 * @param {Condition} c
 */
function _removeVirtualOperator(c) {
    const { negate, path, operator, value } = c;
    if (typeof operator !== "string") {
        return;
    }
    if (["set", "not_set"].includes(operator)) {
        if (value === true) {
            return Condition.of(path, operator === "set" ? "=" : "!=", value, negate);
        }
        return Condition.of(path, operator === "set" ? "!=" : "=", value, negate);
    }
    if (["starts_with", "ends_with"].includes(operator)) {
        return Condition.of(
            path,
            "=ilike",
            operator === "starts_with" ? `${value}%` : `%${value}`,
            negate
        );
    }
    if (["next", "not_next", "last", "not_last"].includes(operator)) {
        const fieldType = value[2];
        const val =
            ["last", "not_last"].includes(operator) && Number.isInteger(value[0])
                ? [-value[0], value[1], value[2]]
                : value;

        const expressions = [
            Expression.of(
                fieldType === "date"
                    ? DATE_TODAY_STRING_EXPRESSION
                    : DATETIME_TODAY_STRING_EXPRESSION
            ),
            getDeltaExpression(val, fieldType),
        ];
        if (["last", "not_last"].includes(operator)) {
            expressions.reverse();
        }
        return Condition.of(
            path,
            ["next", "last"].includes(operator) ? "between" : "is_not_between",
            expressions,
            negate
        );
    }
    if (["today", "not_today"].includes(operator)) {
        if (Array.isArray(value)) {
            return Condition.of(
                path,
                operator === "today" ? "between" : "is_not_between",
                value,
                negate
            );
        } else {
            return Condition.of(path, operator === "today" ? "=" : "!=", value, negate);
        }
    }
}

////////////////////////////////////////////////////////////////////////////////
//  operations on trees
////////////////////////////////////////////////////////////////////////////////

function operate(...args) {
    return ConditionTree.fromDomain("[]");
}

/**
 * @param {ConditionTree} tree
 * @returns {ConditionTree}
 */
export function createBetweenOperators(tree) {
    return operate(
        (connector) => rewriteNConsecutiveChildren(_createBetweenOperator, connector),
        tree,
        {},
        "connector"
    );
}

/**
 * @param {ConditionTree} tree
 * @returns {ConditionTree}
 */
export function removeBetweenOperators(tree) {
    return operate(_removeBetweenOperator, tree);
}

/**
 * @param {ConditionTree} tree
 * @param {Options} [options={}]
 * @returns {ConditionTree}
 */
function createDatetimeOptions(tree, options = {}) {
    return operate(
        (connector) => rewriteNConsecutiveChildren(_createDatetimeOption, connector, options, 3),
        tree,
        options,
        "connector"
    );
}

/**
 * @param {ConditionTree} tree
 * @returns {ConditionTree}
 */
function removeDatetimeOptions(tree) {
    return operate(_removeDatetimeOption, tree);
}

const createVirtualOperatorOp = TargetedOperation.of({
    operateOnCondition: _createVirtualOperator,
});

/**
 * @param {ConditionTree} tree
 * @param {Options} [options=[]]
 * @returns {ConditionTree}
 */
export function createVirtualOperators(tree, options = {}) {
    return createVirtualOperatorOp.operate(tree);
}

const removeVirtualOperatorOp = TargetedOperation.of({
    operateOnCondition: _removeVirtualOperator,
});

/**
 * @param {ConditionTree} tree
 * @returns {ConditionTree}
 */
export function removeVirtualOperators(tree) {
    return removeVirtualOperatorOp.operate(tree);
}

/**
 * @param {ConditionTree} tree
 * @param {Options} [options=[]]
 * @returns {ConditionTree}
 */
function createSpecialPaths(tree, options = {}) {
    return operate(_createSpecialPath, tree, options);
}

/**
 * @param {ConditionTree} tree
 * @returns {ConditionTree}
 */
function removeSpecialPaths(tree) {
    return operate(_removeSpecialPath, tree);
}

////////////////////////////////////////////////////////////////////////////////
//  PUBLIC: MAPPINGS
//    tree <-> expression
//    domain <-> expression
//    expression <-> tree
////////////////////////////////////////////////////////////////////////////////

export const VIRTUAL_OPERATORS_CREATION = [createVirtualOperators, createBetweenOperators];
export const FULL_VIRTUAL_OPERATORS_CREATION = [
    ...VIRTUAL_OPERATORS_CREATION,
    createSpecialPaths,
    createDatetimeOptions,
];

export const VIRTUAL_OPERATORS_DESTRUCTION = [removeBetweenOperators, removeVirtualOperators];
export const FULL_VIRTUAL_OPERATORS_DESTRUCTION = [
    removeDatetimeOptions,
    removeSpecialPaths,
    ...VIRTUAL_OPERATORS_DESTRUCTION,
];
