import { describe, expect, test } from "@odoo/hoot";
import { makeMockEnv } from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import {
    Condition,
    ConditionTree,
    Connector,
    Expression,
} from "@web/core/tree_editor/condition_tree";
import { expressionFromTree, treeFromExpression } from "@web/core/tree_editor/expression_tree";

function expressionFromDomain(domain, options = {}) {
    const tree = ConditionTree.fromDomain(domain, options);
    return expressionFromTree(tree, options);
}

function domainFromExpression(expression, options = {}) {
    const tree = treeFromExpression(expression, options);
    return tree.toDomainRepr();
}

describe.current.tags("headless");

test("toDomainRepr", async () => {
    await makeMockEnv();
    const toTest = [
        {
            tree: Condition.of("foo", "=", false),
            result: `[("foo", "=", False)]`,
        },
        {
            tree: Condition.of("foo", "=", false, true),
            result: `["!", ("foo", "=", False)]`,
        },
        {
            tree: Condition.of("foo", "=?", false),
            result: `[("foo", "=?", False)]`,
        },
        {
            tree: Condition.of("foo", "=?", false, true),
            result: `["!", ("foo", "=?", False)]`,
        },
        {
            tree: Condition.of("foo", "starts_with", "hello"),
            result: `[("foo", "=ilike", "hello%")]`,
        },
        {
            tree: Condition.of("foo", "ends_with", "hello"),
            result: `[("foo", "=ilike", "%hello")]`,
        },
        {
            tree: Condition.of("foo", "between", [1, 3]),
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            tree: Condition.of("foo", "between", [1, Expression.of("uid")], true),
            result: `["!", "&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            tree: Condition.of("foo", "is_not_between", [1, Expression.of("uid")]),
            result: `["|", ("foo", "<", 1), ("foo", ">", uid)]`,
        },
        {
            tree: Condition.of("foo", "is_not_between", [1, 3], true),
            result: `["!", "|", ("foo", "<", 1), ("foo", ">", 3)]`,
        },
        {
            tree: Condition.of("foo", "next", [1, "weeks", "date"]),
            result: `["&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: Condition.of("foo", "last", [1, "months", "date"]),
            result: `["&", ("foo", ">=", (context_today() + relativedelta(months = -1)).strftime("%Y-%m-%d")), ("foo", "<=", context_today().strftime("%Y-%m-%d"))]`,
        },
        {
            tree: Condition.of("foo", "next", [1, "weeks", "datetime"]),
            result: `["&", ("foo", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today() + relativedelta(weeks = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            tree: Condition.of("foo", "last", [1, "months", "datetime"]),
            result: `["&", ("foo", ">=", datetime.datetime.combine(context_today() + relativedelta(months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            tree: Condition.of("foo", "next", [1, "weeks", "date"], true),
            result: `["!", "&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: Condition.of("foo", "last", [Expression.of("a"), "weeks", "date"], true),
            result: `["!", "&", ("foo", ">=", (context_today() + relativedelta(weeks = a)).strftime("%Y-%m-%d")), ("foo", "<=", context_today().strftime("%Y-%m-%d"))]`,
        },
        {
            tree: Condition.of("foo", "next", [1, "b", "date"], true),
            result: `["!", "&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(b = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: Condition.of("foo", "not_next", [1, "weeks", "date"]),
            result: `["|", ("foo", "<", context_today().strftime("%Y-%m-%d")), ("foo", ">", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: Condition.of("foo", "not_next", [1, "weeks", "date"], true),
            result: `["!", "|", ("foo", "<", context_today().strftime("%Y-%m-%d")), ("foo", ">", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: Condition.of("date.__time", "=", false),
            result: `["&", "&", ("date.hour_number", "=", False), ("date.minute_number", "=", False), ("date.second_number", "=", False)]`,
        },
        {
            tree: Condition.of("date.__time", "!=", false),
            result: `["|", "|", ("date.hour_number", "!=", False), ("date.minute_number", "!=", False), ("date.second_number", "!=", False)]`,
        },
        {
            tree: Condition.of("date.__time", "=", "01:15:24"),
            result: `["&", "&", ("date.hour_number", "=", 1), ("date.minute_number", "=", 15), ("date.second_number", "=", 24)]`,
        },
        {
            tree: Condition.of("date.__time", "!=", "01:15:24"),
            result: `["|", "|", ("date.hour_number", "!=", 1), ("date.minute_number", "!=", 15), ("date.second_number", "!=", 24)]`,
        },
        {
            tree: Condition.of("date.__time", "between", ["01:15:24", "22:06:56"]),
            result: `[
                "&",
                    "|", "|",
                            ("date.hour_number", ">=", 1),
                            "&", ("date.hour_number", "=", 1), ("date.minute_number", ">=", 15),
                            "&", "&", ("date.hour_number", "=", 1), ("date.minute_number", "=", 15), ("date.second_number", ">=", 24),
                    "|", "|",
                            ("date.hour_number", "<=", 22),
                            "&", ("date.hour_number", "=", 22), ("date.minute_number", "<=", 6),
                            "&", "&", ("date.hour_number", "=", 22), ("date.minute_number", "=", 6), ("date.second_number", "<=", 56)]`,
        },
    ];
    for (const { tree, result } of toTest) {
        expect(tree.toDomainRepr().replace(/[\s\n]+/g, "")).toBe(result.replace(/[\s\n]+/g, ""));
    }
});

test("toDomainRepr . fromDomain", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `[("foo", "=", False)]`,
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
        },
        {
            domain: `["!", ("foo", "=?", False)]`,
        },
        {
            domain: `[("foo", "=ilike", "%hello")]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            domain: `["&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            domain: `["&", ("foo", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today() + relativedelta(months = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            domain: `["!", "&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            domain: `["!", "|", ("foo", "<", 1), ("foo", ">", uid)]`,
        },
        {
            domain: `["&", "&", ("date.hour_number", "=", False), ("date.minute_number", "=", False), ("date.second_number", "=", False)]`,
        },
        {
            domain: `["&", "&", ("date.hour_number", "!=", False), ("date.minute_number", "!=", False), ("date.second_number", "!=", False)]`,
        },
        {
            domain: `["&", "&", ("date.hour_number", "=", 1), ("date.minute_number", "=", 15), ("date.second_number", "=", 24)]`,
        },
        {
            domain: `["|", "|", ("date.hour_number", "!=", 1), ("date.minute_number", "!=", 15), ("date.second_number", "!=", 24)]`,
        },
        {
            domain: `["&", "&", "&", "&", "&", ("date.hour_number", ">=", 1), ("date.minute_number", ">=", 15), ("date.second_number", ">=", 24), ("date.hour_number", "<=", 22), ("date.minute_number", "<=", 6), ("date.second_number", "<=", 56)]`,
        },
    ];
    for (const { domain, result } of toTest) {
        // @ts-ignore
        expect(ConditionTree.fromDomain(domain).toDomainRepr()).toBe(result || domain);
    }
});

test("expression to domain", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return { type: "any" }; // any field
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
                return { type: "any" }; // any field
            }
            if (["foo_ids", "bar_ids"].includes(name)) {
                return { type: "many2many" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expressionTree: Condition.of("foo", "=", false),
            result: `not foo`,
        },
        {
            expressionTree: Condition.of("foo", "=", false, true),
            result: `foo`,
        },
        {
            expressionTree: Condition.of("foo", "!=", false),
            result: `foo`,
        },
        {
            expressionTree: Condition.of("foo", "!=", false, true),
            result: `not foo`,
        },
        {
            expressionTree: Condition.of("y", "=", false),
            result: `not "y"`,
        },
        {
            expressionTree: Condition.of("foo", "between", [1, 3]),
            result: `foo >= 1 and foo <= 3`,
        },
        {
            expressionTree: Condition.of("foo", "between", [1, Expression.of("uid")], true),
            result: `not ( foo >= 1 and foo <= uid )`,
        },
        {
            expressionTree: Condition.of("foo", "next", [1, "weeks", "date"]),
            result: `foo >= context_today().strftime("%Y-%m-%d") and foo <= (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d")`,
        },
        {
            expressionTree: Condition.of("foo", "last", [1, "weeks", "date"]),
            result: `foo >= (context_today() + relativedelta(weeks = -1)).strftime("%Y-%m-%d") and foo <= context_today().strftime("%Y-%m-%d")`,
        },
        {
            expressionTree: Condition.of("foo", "next", [1, "months", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today() + relativedelta(months = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: Condition.of("foo", "last", [1, "months", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today() + relativedelta(months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: Condition.of("foo", "last", [Expression.of("a"), "months", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today() + relativedelta(months = a), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: Condition.of("foo", "last", [1, "b", "datetime"]),
            result: `foo >= datetime.datetime.combine(context_today() + relativedelta(b = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and foo <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
        },
        {
            expressionTree: Expression.of("uid"),
            result: `uid`,
        },
        {
            expressionTree: Condition.of("foo_ids", "in", []),
            result: `set(foo_ids).intersection([])`,
        },
        {
            expressionTree: Condition.of("foo_ids", "in", [1]),
            result: `set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: Condition.of("foo_ids", "in", 1),
            result: `set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: Condition.of("foo", "in", []),
            result: `foo in []`,
        },
        {
            expressionTree: Condition.of(Expression.of("expr"), "in", []),
            result: `expr in []`,
        },
        {
            expressionTree: Condition.of("foo", "in", [1]),
            result: `foo in [1]`,
        },
        {
            expressionTree: Condition.of("foo", "in", 1),
            result: `foo in [1]`,
        },
        {
            expressionTree: Condition.of("foo", "in", Expression.of("expr")),
            result: `foo in expr`,
        },
        {
            expressionTree: Condition.of("foo_ids", "in", Expression.of("expr")),
            result: `set(foo_ids).intersection(expr)`,
        },
        {
            expressionTree: Condition.of("y", "in", []),
            result: `"y" in []`,
        },
        {
            expressionTree: Condition.of("y", "in", [1]),
            result: `"y" in [1]`,
        },
        {
            expressionTree: Condition.of("y", "in", 1),
            result: `"y" in [1]`,
        },
        {
            expressionTree: Condition.of("foo_ids", "not in", []),
            result: `not set(foo_ids).intersection([])`,
        },
        {
            expressionTree: Condition.of("foo_ids", "not in", [1]),
            result: `not set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: Condition.of("foo_ids", "not in", 1),
            result: `not set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: Condition.of("foo", "not in", []),
            result: `foo not in []`,
        },
        {
            expressionTree: Condition.of("foo", "not in", [1]),
            result: `foo not in [1]`,
        },
        {
            expressionTree: Condition.of("foo", "not in", 1),
            result: `foo not in [1]`,
        },
        {
            expressionTree: Condition.of("y", "not in", []),
            result: `"y" not in []`,
        },
        {
            expressionTree: Condition.of("y", "not in", [1]),
            result: `"y" not in [1]`,
        },
        {
            expressionTree: Condition.of("y", "not in", 1),
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
                return { type: "any" }; // any field
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
            result: Condition.of("foo", "not_set", false),
        },
        {
            expression: `foo == False`,
            result: Condition.of("foo", "not_set", false),
        },
        {
            expression: `foo`,
            result: Condition.of("foo", "set", false),
        },
        {
            expression: `foo == True`,
            result: Condition.of("foo", "=", true),
        },
        {
            expression: `foo is True`,
            result: Expression.of(`foo is True`),
        },
        {
            expression: `not (foo == False)`,
            result: Condition.of("foo", "set", false),
        },
        {
            expression: `not (not foo)`,
            result: Condition.of("foo", "set", false),
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: Condition.of("foo", "between", [1, 3]),
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: Condition.of("foo", "between", [1, Expression.of("uid")]),
        },
        {
            expression: `foo < 1 or foo > 3`,
            result: Condition.of("foo", "is_not_between", [1, 3]),
        },
        {
            expression: `date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")`,
            result: Condition.of("date_field", "next", [1, "years", "date"]),
        },
        {
            expression: `date_field < context_today().strftime("%Y-%m-%d") or date_field > (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")`,
            result: Condition.of("date_field", "not_next", [1, "years", "date"]),
        },
        {
            expression: `datetime_field >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field <= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: Condition.of("datetime_field", "next", [1, "years", "datetime"]),
        },
        {
            // Case where the <= is first: this is not changed to a between, and so not changed to a within either
            expression: `datetime_field <= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: Connector.of("&", [
                Condition.of(
                    "datetime_field",
                    "<=",
                    Expression.of(
                        `datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                Condition.of(
                    "datetime_field",
                    ">=",
                    Expression.of(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
        },
        {
            expression: `datetime_field >= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: Condition.of("datetime_field", "last", [-1, "years", "datetime"]),
        },
        {
            expression: `(date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")) and (date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 2)).strftime("%Y-%m-%d"))`,
            result: Connector.of("&", [
                Condition.of("date_field", "next", [1, "years", "date"]),
                Condition.of("date_field", "next", [2, "years", "date"]),
            ]),
        },
        {
            expression: `(date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")) or (date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 2)).strftime("%Y-%m-%d"))`,
            result: Connector.of("|", [
                Condition.of("date_field", "next", [1, "years", "date"]),
                Condition.of("date_field", "next", [2, "years", "date"]),
            ]),
        },
        {
            expression: `foo >= 1 if bar else foo <= uid`,
            result: Connector.of("|", [
                Connector.of("&", [
                    Condition.of("bar", "set", false),
                    Condition.of("foo", ">=", 1),
                ]),
                Connector.of("&", [
                    Condition.of("bar", "not_set", false),
                    Condition.of("foo", "<=", Expression.of("uid")),
                ]),
            ]),
        },
        {
            expression: `context.get('toto')`,
            result: Expression.of(`context.get("toto")`),
        },
        {
            expression: `not context.get('toto')`,
            result: Expression.of(`not context.get("toto")`),
        },
        {
            expression: `foo >= 1 if context.get('toto') else bar == 42`,
            result: Connector.of("|", [
                Connector.of("&", [
                    Expression.of(`context.get("toto")`),
                    Condition.of("foo", ">=", 1),
                ]),
                Connector.of("&", [
                    Expression.of(`not context.get("toto")`),
                    Condition.of("bar", "=", 42),
                ]),
            ]),
        },
        {
            expression: `set()`,
            result: Expression.of(`set()`),
        },
        {
            expression: `set([1, 2])`,
            result: Expression.of(`set([1, 2])`),
        },
        {
            expression: `set(foo_ids).intersection([1, 2])`,
            result: Condition.of("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(foo_ids).intersection(set([1, 2]))`,
            result: Condition.of("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(foo_ids).intersection(set((1, 2)))`,
            result: Condition.of("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(foo_ids).intersection("ab")`,
            result: Expression.of(`set(foo_ids).intersection("ab")`),
        },
        {
            expression: `set([1, 2]).intersection(foo_ids)`,
            result: Condition.of("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set(set([1, 2])).intersection(foo_ids)`,
            result: Condition.of("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set((1, 2)).intersection(foo_ids)`,
            result: Condition.of("foo_ids", "in", [1, 2]),
        },
        {
            expression: `set("ab").intersection(foo_ids)`,
            result: Expression.of(`set("ab").intersection(foo_ids)`),
        },
        {
            expression: `set([2, 3]).intersection([1, 2])`,
            result: Expression.of(`set([2, 3]).intersection([1, 2])`),
        },
        {
            expression: `set(foo_ids).intersection(bar_ids)`,
            result: Expression.of(`set(foo_ids).intersection(bar_ids)`),
        },
        {
            expression: `set().intersection(foo_ids)`,
            result: Condition.of(0, "=", 1),
        },
        {
            expression: `set(foo_ids).intersection()`,
            result: Condition.of("foo_ids", "set", false),
        },
        {
            expression: `not set().intersection(foo_ids)`,
            result: Condition.of(1, "=", 1),
        },
        {
            expression: `not set(foo_ids).intersection()`,
            result: Condition.of("foo_ids", "not_set", false),
        },
        {
            expression: `not set(foo_ids).intersection([1, 2])`,
            result: Condition.of("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(foo_ids).intersection(set([1, 2]))`,
            result: Condition.of("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(foo_ids).intersection(set((1, 2)))`,
            result: Condition.of("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(foo_ids).intersection("ab")`,
            result: Expression.of(`not set(foo_ids).intersection("ab")`),
        },
        {
            expression: `not set([1, 2]).intersection(foo_ids)`,
            result: Condition.of("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set(set([1, 2])).intersection(foo_ids)`,
            result: Condition.of("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set((1, 2)).intersection(foo_ids)`,
            result: Condition.of("foo_ids", "not in", [1, 2]),
        },
        {
            expression: `not set("ab").intersection(foo_ids)`,
            result: Expression.of(`not set("ab").intersection(foo_ids)`),
        },
        {
            expression: `not set([2, 3]).intersection([1, 2])`,
            result: Expression.of(`not set([2, 3]).intersection([1, 2])`),
        },
        {
            expression: `not set(foo_ids).intersection(bar_ids)`,
            result: Expression.of(`not set(foo_ids).intersection(bar_ids)`),
        },
        {
            expression: `set(foo_ids).difference([1, 2])`,
            result: Expression.of(`set(foo_ids).difference([1, 2])`),
        },
        {
            expression: `set(foo_ids).union([1, 2])`,
            result: Expression.of(`set(foo_ids).union([1, 2])`),
        },
        {
            expression: `expr in []`,
            result: Expression.of(`expr in []`),
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
                return { type: "any" }; // any field
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

test("domain to expression", () => {
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

test("evaluation . expressionFromTree = contains . toDomainRepr", () => {
    const options = {
        getFieldDef: (name) => {
            if (name === "foo") {
                return { type: "any" }; // any field
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
        Condition.of("foo", "=", false),
        Condition.of("foo", "=", false, true),
        Condition.of("foo", "!=", false),
        Condition.of("foo", "!=", false, true),
        Condition.of("y", "=", false),
        Condition.of("foo", "between", [1, 3]),
        Condition.of("foo", "between", [1, Expression.of("uid")], true),
        Condition.of("foo", "is_not_between", [1, 3]),
        Condition.of("datefield", "next", [1, "weeks", "date"]),
        Condition.of("datetimefield", "last", [1, "years", "datetime"]),
        Condition.of("datetimefield", "not_last", [1, "years", "datetime"]),
        Condition.of("foo_ids", "in", []),
        Condition.of("foo_ids", "in", [1]),
        Condition.of("foo_ids", "in", 1),
        Condition.of("foo", "in", []),
        Condition.of(Expression.of("expr"), "in", []),
        Condition.of("foo", "in", [1]),
        Condition.of("foo", "in", 1),
        Condition.of("y", "in", []),
        Condition.of("y", "in", [1]),
        Condition.of("y", "in", 1),
        Condition.of("foo_ids", "not in", []),
        Condition.of("foo_ids", "not in", [1]),
        Condition.of("foo_ids", "not in", 1),
        Condition.of("foo", "not in", []),
        Condition.of("foo", "not in", [1]),
        Condition.of("foo", "not in", 1),
        Condition.of("y", "not in", []),
        Condition.of("y", "not in", [1]),
        Condition.of("y", "not in", 1),
        Condition.of("foo", "in", Expression.of("expr2")),
        Condition.of("foo_ids", "in", Expression.of("expr2")),
    ];
    for (const tree of toTest) {
        expect(evaluateBooleanExpr(expressionFromTree(tree, options), record)).toBe(
            new Domain(tree.toDomainRepr()).contains(record)
        );
    }
});
