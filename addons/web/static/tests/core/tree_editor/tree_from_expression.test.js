import { expect, test } from "@odoo/hoot";

import {
    complexCondition,
    condition,
    connector,
    expression,
} from "@web/core/tree_editor/condition_tree";
import { treeFromExpression } from "@web/core/tree_editor/tree_from_expression";

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
            expression: `foo < 1 or foo > 3`,
            result: condition("foo", "not_between", [1, 3]),
        },
        {
            expression: `date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")`,
            result: condition("date_field", "next", [1, "years", "date"]),
        },
        {
            expression: `date_field < context_today().strftime("%Y-%m-%d") or date_field > (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")`,
            result: condition("date_field", "not_next", [1, "years", "date"]),
        },
        {
            expression: `datetime_field >= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field <= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: condition("datetime_field", "next", [1, "years", "datetime"]),
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
            expression: `datetime_field >= datetime.datetime.combine(context_today() + relativedelta(years = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S") and datetime_field <= datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
            result: condition("datetime_field", "last", [-1, "years", "datetime"]),
        },
        {
            expression: `(date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")) and (date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 2)).strftime("%Y-%m-%d"))`,
            result: connector("&", [
                condition("date_field", "next", [1, "years", "date"]),
                condition("date_field", "next", [2, "years", "date"]),
            ]),
        },
        {
            expression: `(date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 1)).strftime("%Y-%m-%d")) or (date_field >= context_today().strftime("%Y-%m-%d") and date_field <= (context_today() + relativedelta(years = 2)).strftime("%Y-%m-%d"))`,
            result: connector("|", [
                condition("date_field", "next", [1, "years", "date"]),
                condition("date_field", "next", [2, "years", "date"]),
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
