import { expect, test, describe } from "@odoo/hoot";

import { Domain } from "@web/core/domain";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import {
    complexCondition,
    condition,
    connector,
    domainFromExpression,
    domainFromTree,
    expression,
    expressionFromDomain,
    expressionFromTree,
    treeFromDomain,
    treeFromExpression,
} from "@web/core/tree_editor/condition_tree";

describe.current.tags("headless");

test("domainFromTree", () => {
    const toTest = [
        {
            tree: condition("foo", "=", false),
            result: `[("foo", "=", False)]`,
        },
        {
            tree: condition("foo", "=", false, true),
            result: `["!", ("foo", "=", False)]`,
        },
        {
            tree: condition("foo", "=?", false),
            result: `[("foo", "=?", False)]`,
        },
        {
            tree: condition("foo", "=?", false, true),
            result: `["!", ("foo", "=?", False)]`,
        },
        {
            tree: condition("foo", "starts_with", "hello"),
            result: `[("foo", "=ilike", "hello%")]`,
        },
        {
            tree: condition("foo", "ends_with", "hello"),
            result: `[("foo", "=ilike", "%hello")]`,
        },
        {
            tree: condition("foo", "between", [1, 3]),
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            tree: condition("foo", "between", [1, expression("uid")], true),
            result: `["!", "&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            tree: condition("foo", "within", [1, "weeks", "date"]),
            result: `["&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "within", [-1, "months", "date"]),
            result: `["&", ("foo", ">=", (context_today() + relativedelta(months = -1)).strftime("%Y-%m-%d")), ("foo", "<=", context_today().strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "within", [1, "weeks", "datetime"]),
            result: `["&", ("foo", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today() + relativedelta(weeks = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            tree: condition("foo", "within", [-1, "months", "datetime"]),
            result: `["&", ("foo", ">=", datetime.datetime.combine(context_today() + relativedelta(months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            tree: condition("foo", "within", [1, "weeks", "date"], true),
            result: `["!", "&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "within", [expression("a"), "weeks", "date"], true),
            result: `["!", "&", ("foo", ">=", (context_today() + relativedelta(weeks = a)).strftime("%Y-%m-%d")), ("foo", "<=", context_today().strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "within", [1, "b", "date"], true),
            result: `["!", "&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(b = 1)).strftime("%Y-%m-%d"))]`,
        },
    ];
    for (const { tree, result } of toTest) {
        expect(domainFromTree(tree)).toBe(result);
    }
});

test("domainFromTree . treeFromDomain", () => {
    const toTest = [
        {
            domain: `[("foo", "=", False)]`,
            result: `[("foo", "=", False)]`,
        },
        {
            domain: `[("foo", "=", true)]`,
            result: `[("foo", "=", True)]`,
        },
        {
            domain: `["!", ("foo", "=", False)]`,
            result: `[("foo", "!=", False)]`,
        },
        {
            domain: `[("foo", "=?", False)]`,
            result: `[("foo", "=?", False)]`,
        },
        {
            domain: `["!", ("foo", "=?", False)]`,
            result: `["!", ("foo", "=?", False)]`,
        },
        {
            domain: `[("foo", "=ilike", "%hello")]`,
            result: `[("foo", "=ilike", "%hello")]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            domain: `["&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
            result: `["&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            domain: `["&", ("foo", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today() + relativedelta(months = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
            result: `["&", ("foo", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today() + relativedelta(months = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
    ];
    for (const { domain, result } of toTest) {
        expect(domainFromTree(treeFromDomain(domain))).toBe(result);
    }
});

test("domainFromExpression", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return {}; // any field
            }
            if (name === "foo_ids") {
                return { type: "many2many" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expression: `not foo`,
            result: `[("foo", "=", False)]`,
        },
        {
            expression: `foo == False`,
            result: `[("foo", "=", False)]`,
        },
        {
            expression: `foo`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `foo == True`,
            result: `[("foo", "=", True)]`,
        },
        {
            expression: `foo is True`,
            result: `[(bool(foo is True), "=", 1)]`,
        },
        {
            expression: `not (foo == False)`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `not (not foo)`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            expression: `foo >= 1 if foo else foo <= uid`,
            result: `["|", "&", ("foo", "!=", False), ("foo", ">=", 1), "&", ("foo", "=", False), ("foo", "<=", uid)]`,
        },
        {
            expression: `context.get('toto')`,
            result: `[(bool(context.get("toto")), "=", 1)]`,
        },
        {
            expression: `foo >= 1 if context.get('toto') else bar == 42`,
            result: `["|", "&", (bool(context.get("toto")), "=", 1), ("foo", ">=", 1), "&", (not context.get("toto"), "=", 1), ("bar", "=", 42)]`,
        },
        {
            expression: `not context.get('toto')`,
            result: `[(not context.get("toto"), "=", 1)]`,
        },
        {
            expression: `True`,
            result: `[(1, "=", 1)]`,
        },
        {
            expression: `False`,
            result: `[(0, "=", 1)]`,
        },
        {
            expression: `A`,
            result: `[(bool(A), "=", 1)]`,
        },
        {
            expression: `foo`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `not A`,
            result: `[(not A, "=", 1)]`,
        },
        {
            expression: `not not A`,
            result: `[(bool(A), "=", 1)]`,
        },
        {
            expression: `y == 2`,
            result: `[(bool(y == 2), "=", 1)]`,
        },
        {
            expression: `not (y == 2)`,
            result: `[(bool(y != 2), "=", 1)]`,
        },
        {
            expression: `foo == 2`,
            result: `[("foo", "=", 2)]`,
        },
        {
            expression: `not (foo == 2)`,
            result: `[("foo", "!=", 2)]`,
        },
        {
            expression: `2 == foo`,
            result: `[("foo", "=", 2)]`,
        },
        {
            expression: `not (2 == foo)`,
            result: `[("foo", "!=", 2)]`,
        },
        {
            expression: `foo < 2`,
            result: `[("foo", "<", 2)]`,
        },
        {
            expression: `not (foo < 2)`,
            result: `[("foo", ">=", 2)]`,
        },
        {
            expression: `2 < foo`,
            result: `[("foo", ">", 2)]`,
        },
        {
            expression: `not (2 < foo)`,
            result: `[("foo", "<=", 2)]`,
        },
        {
            expression: `not(y == 1)`,
            result: `[(bool(y != 1), "=", 1)]`,
        },
        {
            expression: `A if B else C`,
            result: `["|", "&", (bool(B), "=", 1), (bool(A), "=", 1), "&", (not B, "=", 1), (bool(C), "=", 1)]`,
        },
        {
            expression: `not bool(A)`,
            result: `[(not A, "=", 1)]`,
        },
        {
            expression: `not(A and not B)`,
            result: `["!", "&", (bool(A), "=", 1), (not B, "=", 1)]`,
        },
        {
            expression: `not (A and not B)`,
            result: `["|", (not A, "=", 1), (bool(B), "=", 1)]`,
            extraOptions: { distributeNot: true },
        },
    ];
    for (const { expression, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        expect(domainFromExpression(expression, o)).toBe(result);
    }
});

test("expressionFromTree", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return {}; // any field
            }
            if (["foo_ids", "bar_ids"].includes(name)) {
                return { type: "many2many" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expressionTree: condition("foo", "=", false),
            result: `not foo`,
        },
        {
            expressionTree: condition("foo", "=", false, true),
            result: `foo`,
        },
        {
            expressionTree: condition("foo", "!=", false),
            result: `foo`,
        },
        {
            expressionTree: condition("foo", "!=", false, true),
            result: `not foo`,
        },
        {
            expressionTree: condition("y", "=", false),
            result: `not "y"`,
        },
        {
            expressionTree: condition("foo", "between", [1, 3]),
            result: `foo >= 1 and foo <= 3`,
        },
        {
            expressionTree: condition("foo", "between", [1, expression("uid")], true),
            result: `not ( foo >= 1 and foo <= uid )`,
        },
        {
            expressionTree: condition("foo", "within", [1, "weeks", "date"]),
            result: `foo >= context_today().strftime("%Y-%m-%d") and foo <= (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d")`,
        },
        {
            expressionTree: condition("foo", "within", [-1, "weeks", "date"]),
            result: `foo >= (context_today() + relativedelta(weeks = -1)).strftime("%Y-%m-%d") and foo <= context_today().strftime("%Y-%m-%d")`,
        },
        {
            expressionTree: condition("foo", "within", [1, "months", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today() + relativedelta(months = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: condition("foo", "within", [-1, "months", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today() + relativedelta(months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: condition("foo", "within", [expression("a"), "months", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today() + relativedelta(months = a), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: condition("foo", "within", [-1, "b", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today() + relativedelta(b = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: complexCondition("uid"),
            result: `uid`,
        },
        {
            expressionTree: condition("foo_ids", "in", []),
            result: `set(foo_ids).intersection([])`,
        },
        {
            expressionTree: condition("foo_ids", "in", [1]),
            result: `set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo_ids", "in", 1),
            result: `set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo", "in", []),
            result: `foo in []`,
        },
        {
            expressionTree: condition(expression("expr"), "in", []),
            result: `expr in []`,
        },
        {
            expressionTree: condition("foo", "in", [1]),
            result: `foo in [1]`,
        },
        {
            expressionTree: condition("foo", "in", 1),
            result: `foo in [1]`,
        },
        {
            expressionTree: condition("foo", "in", expression("expr")),
            result: `foo in expr`,
        },
        {
            expressionTree: condition("foo_ids", "in", expression("expr")),
            result: `set(foo_ids).intersection(expr)`,
        },
        {
            expressionTree: condition("y", "in", []),
            result: `"y" in []`,
        },
        {
            expressionTree: condition("y", "in", [1]),
            result: `"y" in [1]`,
        },
        {
            expressionTree: condition("y", "in", 1),
            result: `"y" in [1]`,
        },
        {
            expressionTree: condition("foo_ids", "not in", []),
            result: `not set(foo_ids).intersection([])`,
        },
        {
            expressionTree: condition("foo_ids", "not in", [1]),
            result: `not set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo_ids", "not in", 1),
            result: `not set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo", "not in", []),
            result: `foo not in []`,
        },
        {
            expressionTree: condition("foo", "not in", [1]),
            result: `foo not in [1]`,
        },
        {
            expressionTree: condition("foo", "not in", 1),
            result: `foo not in [1]`,
        },
        {
            expressionTree: condition("y", "not in", []),
            result: `"y" not in []`,
        },
        {
            expressionTree: condition("y", "not in", [1]),
            result: `"y" not in [1]`,
        },
        {
            expressionTree: condition("y", "not in", 1),
            result: `"y" not in [1]`,
        },
    ];
    for (const { expressionTree, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        expect(expressionFromTree(expressionTree, o)).toBe(result);
    }
});

test("treeFromExpression", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return {}; // any field
            }
            if (["foo_ids", "bar_ids"].includes(name)) {
                return { type: "many2many" };
            }
            if (name === "date_field") {
                return { type: "date" };
            }
            if (name === "datetime_field") {
                return { type: "datetime" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expression: `not foo`,
            result: condition("foo", "not_set", false),
        },
        {
            expression: `foo == False`,
            result: condition("foo", "not_set", false),
        },
        {
            expression: `foo`,
            result: condition("foo", "set", false),
        },
        {
            expression: `foo == True`,
            result: condition("foo", "=", true),
        },
        {
            expression: `foo is True`,
            result: complexCondition(`foo is True`),
        },
        {
            expression: `not (foo == False)`,
            result: condition("foo", "set", false),
        },
        {
            expression: `not (not foo)`,
            result: condition("foo", "set", false),
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: condition("foo", "between", [1, 3]),
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: condition("foo", "between", [1, expression("uid")]),
        },
        {
            expression: `date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")`,
            result: condition("date_field", "within", [1, "years", "date"]),
        },
        {
            expression: `datetime_field >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field <= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: condition("datetime_field", "within", [1, "years", "datetime"]),
        },
        {
            // Case where the <= is first: this is not changed to a between, and so not changed to a within either
            expression: `datetime_field <= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: connector("&", [
                condition(
                    "datetime_field",
                    "<=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_field",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
        },
        {
            // Case where the within doesn't have the period amount with the right sign, so this invalid within becomes a between
            expression: `datetime_field >= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: condition("datetime_field", "between", [
                expression(
                    "datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime('%Y-%m-%d %H:%M:%S')"
                ),
                expression(
                    "datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime('%Y-%m-%d %H:%M:%S')"
                ),
            ]),
        },
        {
            expression: `(date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")) and (date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 2)).strftime("%Y-%m-%d"))`,
            result: connector("&", [
                condition("date_field", "within", [1, "years", "date"]),
                condition("date_field", "within", [2, "years", "date"]),
            ]),
        },
        {
            expression: `(date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")) or (date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 2)).strftime("%Y-%m-%d"))`,
            result: connector("|", [
                condition("date_field", "within", [1, "years", "date"]),
                condition("date_field", "within", [2, "years", "date"]),
            ]),
        },
        {
            expression: `foo >= 1 if bar else foo <= uid`,
            result: connector("|", [
                connector("&", [condition("bar", "set", false), condition("foo", ">=", 1)]),
                connector("&", [
                    condition("bar", "not_set", false),
                    condition("foo", "<=", expression("uid")),
                ]),
            ]),
        },
        {
            expression: `context.get('toto')`,
            result: complexCondition(`context.get("toto")`),
        },
        {
            expression: `not context.get('toto')`,
            result: complexCondition(`not context.get("toto")`),
        },
        {
            expression: `foo >= 1 if context.get('toto') else bar == 42`,
            result: connector("|", [
                connector("&", [
                    complexCondition(`context.get("toto")`),
                    condition("foo", ">=", 1),
                ]),
                connector("&", [
                    complexCondition(`not context.get("toto")`),
                    condition("bar", "=", 42),
                ]),
            ]),
        },
        {
            expression: `set()`,
            result: complexCondition(`set()`),
        },
        {
            expression: `set([1, 2])`,
            result: complexCondition(`set([1, 2])`),
        },
        {
            expression: `set(foo_ids).intersection([1, 2])`,
            result: condition("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(foo_ids).intersection(set([1, 2]))`,
            result: condition("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(foo_ids).intersection(set((1, 2)))`,
            result: condition("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(foo_ids).intersection("ab")`,
            result: complexCondition(`set(foo_ids).intersection("ab")`),
        },
        {
            expression: `set([1, 2]).intersection(foo_ids)`,
            result: condition("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(set([1, 2])).intersection(foo_ids)`,
            result: condition("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set((1, 2)).intersection(foo_ids)`,
            result: condition("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set("ab").intersection(foo_ids)`,
            result: complexCondition(`set("ab").intersection(foo_ids)`),
        },
        {
            expression: `set([2, 3]).intersection([1, 2])`,
            result: complexCondition(`set([2, 3]).intersection([1, 2])`),
        },
        {
            expression: `set(foo_ids).intersection(bar_ids)`,
            result: complexCondition(`set(foo_ids).intersection(bar_ids)`),
        },
        {
            expression: `set().intersection(foo_ids)`,
            result: condition(0, "=", 1),
        },
        {
            expression: `set(foo_ids).intersection()`,
            result: condition("foo_ids", "set", false),
        },
        {
            expression: `not set().intersection(foo_ids)`,
            result: condition(1, "=", 1),
        },
        {
            expression: `not set(foo_ids).intersection()`,
            result: condition("foo_ids", "not_set", false),
        },
        {
            expression: `not set(foo_ids).intersection([1, 2])`,
            result: condition("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(foo_ids).intersection(set([1, 2]))`,
            result: condition("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(foo_ids).intersection(set((1, 2)))`,
            result: condition("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(foo_ids).intersection("ab")`,
            result: complexCondition(`not set(foo_ids).intersection("ab")`),
        },
        {
            expression: `not set([1, 2]).intersection(foo_ids)`,
            result: condition("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(set([1, 2])).intersection(foo_ids)`,
            result: condition("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set((1, 2)).intersection(foo_ids)`,
            result: condition("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set("ab").intersection(foo_ids)`,
            result: complexCondition(`not set("ab").intersection(foo_ids)`),
        },
        {
            expression: `not set([2, 3]).intersection([1, 2])`,
            result: complexCondition(`not set([2, 3]).intersection([1, 2])`),
        },
        {
            expression: `not set(foo_ids).intersection(bar_ids)`,
            result: complexCondition(`not set(foo_ids).intersection(bar_ids)`),
        },
        {
            expression: `set(foo_ids).difference([1, 2])`,
            result: complexCondition(`set(foo_ids).difference([1, 2])`),
        },
        {
            expression: `set(foo_ids).union([1, 2])`,
            result: complexCondition(`set(foo_ids).union([1, 2])`),
        },
        {
            expression: `expr in []`,
            result: complexCondition(`expr in []`),
        },
    ];
    for (const { expression, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        expect(treeFromExpression(expression, o)).toEqual(result);
    }
});

test("expressionFromTree . treeFromExpression", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return {}; // any field
            }
            if (name === "foo_ids") {
                return { type: "many2many" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expression: `not foo`,
            result: `not foo`,
        },
        {
            expression: `foo == False`,
            result: `not foo`,
        },
        {
            expression: `foo == None`,
            result: `foo == None`,
        },
        {
            expression: `foo is None`,
            result: `foo is None`,
        },
        {
            expression: `foo`,
            result: `foo`,
        },
        {
            expression: `foo == True`,
            result: `foo == True`,
        },
        {
            expression: `foo is True`,
            result: `foo is True`,
        },
        {
            expression: `not (foo == False)`,
            result: `foo`,
        },
        {
            expression: `not (not foo)`,
            result: `foo`,
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: `foo >= 1 and foo <= 3`,
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: `foo >= 1 and foo <= uid`,
        },
        {
            expression: `foo >= 1 if glob else foo <= uid`,
            result: `foo >= 1 if glob else foo <= uid`,
        },
        {
            expression: `context.get("toto")`,
            result: `context.get("toto")`,
        },
        {
            expression: `foo >= 1 if context.get("toto") else bar == 42`,
            result: `foo >= 1 if context.get("toto") else bar == 42`,
        },
        {
            expression: `not context.get("toto")`,
            result: `not context.get("toto")`,
        },
        {
            expression: `set()`,
            result: `set()`,
        },
        {
            expression: `set([1, 2])`,
            result: `set([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection([1, 2])`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection(set([1, 2]))`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection(set((1, 2)))`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection("ab")`,
            result: `set(foo_ids).intersection("ab")`,
        },
        {
            expression: `set([1, 2]).intersection(foo_ids)`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(set([1, 2])).intersection(foo_ids)`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set((1, 2)).intersection(foo_ids)`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set("ab").intersection(foo_ids)`,
            result: `set("ab").intersection(foo_ids)`,
        },
        {
            expression: `set([2, 3]).intersection([1, 2])`,
            result: `set([2, 3]).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection(bar_ids)`,
            result: `set(foo_ids).intersection(bar_ids)`,
        },
        {
            expression: `set().intersection(foo_ids)`,
            result: `False`,
        },
        {
            expression: `set(foo_ids).intersection()`,
            result: `foo_ids`,
        },
        {
            expression: `not set(foo_ids).intersection([1, 2])`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection(set([1, 2]))`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection(set((1, 2)))`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection("ab")`,
            result: `not set(foo_ids).intersection("ab")`,
        },
        {
            expression: `not set([1, 2]).intersection(foo_ids)`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(set([1, 2])).intersection(foo_ids)`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set((1, 2)).intersection(foo_ids)`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set("ab").intersection(foo_ids)`,
            result: `not set("ab").intersection(foo_ids)`,
        },
        {
            expression: `not set([2, 3]).intersection([1, 2])`,
            result: `not set([2, 3]).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection(bar_ids)`,
            result: `not set(foo_ids).intersection(bar_ids)`,
        },
        {
            expression: `set(foo_ids).difference([1, 2])`,
            result: `set(foo_ids).difference([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection([1, 2])`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set([foo]).intersection()`,
            result: `foo`,
        },
        {
            expression: `set([foo]).intersection([1, 2])`,
            result: `foo in [1, 2]`,
        },
        {
            expression: `set().intersection([foo])`,
            result: `False`,
        },
        {
            expression: `set([1, 2]).intersection([foo])`,
            result: `foo in [1, 2]`,
        },
        {
            expression: `not set([foo]).intersection()`,
            result: `not foo`,
        },
        {
            expression: `not set([foo]).intersection([1, 2])`,
            result: `foo not in [1, 2]`,
        },
        {
            expression: `not set().intersection([foo])`,
            result: `True`,
        },
        {
            expression: `not set([1, 2]).intersection([foo])`,
            result: `foo not in [1, 2]`,
        },
    ];
    for (const { expression, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        expect(expressionFromTree(treeFromExpression(expression, o), o)).toBe(result);
    }
});

test("expressionFromDomain", () => {
    const options = {
        getFieldDef: (name) => (name === "x" ? {} : null),
    };
    const toTest = [
        {
            domain: `[(1, "=", 1)]`,
            result: `True`,
        },
        {
            domain: `[(0, "=", 1)]`,
            result: `False`,
        },
        {
            domain: `[("A", "=", 1)]`,
            result: `"A" == 1`,
        },
        {
            domain: `[(bool(A), "=", 1)]`,
            result: `bool(A)`,
        },
        {
            domain: `[("x", "=", 2)]`,
            result: `x == 2`,
        },
    ];

    for (const { domain, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        expect(expressionFromDomain(domain, o)).toBe(result);
    }
});

test("evaluation . expressionFromTree = contains . domainFromTree", () => {
    const options = {
        getFieldDef: (name) => {
            if (name === "foo") {
                return {}; // any field
            }
            if (name === "foo_ids") {
                return { type: "many2many" };
            }
            if (name === "date_field") {
                return { type: "date" };
            }
            if (name === "datetime_field") {
                return { type: "datetime" };
            }
            return null;
        },
    };

    const record = {
        foo: 1,
        foo_ids: [1, 2],
        uid: 7,
        expr: "abc",
        expr2: [1],
        datefield: "2024-02-05 00:00:00",
        datetimefield: "2024-02-05",
    };

    const toTest = [
        condition("foo", "=", false),
        condition("foo", "=", false, true),
        condition("foo", "!=", false),
        condition("foo", "!=", false, true),
        condition("y", "=", false),
        condition("foo", "between", [1, 3]),
        condition("foo", "between", [1, expression("uid")], true),
        condition("datefield", "within", [1, "weeks", "date"]),
        condition("datetimefield", "within", [-1, "years", "datetime"]),
        condition("foo_ids", "in", []),
        condition("foo_ids", "in", [1]),
        condition("foo_ids", "in", 1),
        condition("foo", "in", []),
        condition(expression("expr"), "in", []),
        condition("foo", "in", [1]),
        condition("foo", "in", 1),
        condition("y", "in", []),
        condition("y", "in", [1]),
        condition("y", "in", 1),
        condition("foo_ids", "not in", []),
        condition("foo_ids", "not in", [1]),
        condition("foo_ids", "not in", 1),
        condition("foo", "not in", []),
        condition("foo", "not in", [1]),
        condition("foo", "not in", 1),
        condition("y", "not in", []),
        condition("y", "not in", [1]),
        condition("y", "not in", 1),
        condition("foo", "in", expression("expr2")),
        condition("foo_ids", "in", expression("expr2")),
    ];
    for (const tree of toTest) {
        expect(evaluateBooleanExpr(expressionFromTree(tree, options), record)).toBe(
            new Domain(domainFromTree(tree)).contains(record)
        );
    }
});
