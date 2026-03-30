import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { Domain } from "@web/core/domain";
import { condition, connector, expression } from "@web/core/tree_editor/condition_tree";
import { constructDomainFromTree } from "@web/core/tree_editor/construct_domain_from_tree";
import {
    eliminateVirtualOperators,
    introduceVirtualOperators,
} from "@web/core/tree_editor/virtual_operators";
import { pyDateStr, pyDatetimeStr } from "./condition_tree_editor_test_helpers";

describe.current.tags("headless");

const options = {
    getFieldDef: (name) => {
        if (name === "m2o") {
            return { type: "many2one" };
        }
        if (name === "m2o.date_2" || name === "date_1" || name === "date_2" || name === "date_3") {
            return { type: "date" };
        }
        if (name === "m2o.dt_2" || name === "dt_1" || name === "dt_2" || name === "dt_3") {
            return { type: "datetime" };
        }
        return null;
    },
};
const fullOptions = { ...options, generateSmartDates: false };

const DATE_START = "2025-07-02 00:00:00";
const DATE_END = "2025-07-03 00:00:00";
const complexPath = expression("path");

const pyDate = (delta) => expression(pyDateStr(delta));
const pyDatetime = (delta) => expression(pyDatetimeStr(delta));

const and = (c, negate) => connector("&", c, negate);
const or = (c, negate) => connector("|", c, negate);
const inRange = (f, v, negate) => condition(f, "in range", v, negate);
const m2oAny = (c, negate = false) => condition("m2o", "any", c, negate);

test(`"in range" operator: no introduction for complex paths (generateSmartDates=false)`, async () => {
    const toTest = [
        {
            tree_py: and([
                condition(complexPath, ">=", DATE_START),
                condition(complexPath, "<=", DATE_END),
            ]),
        },
        {
            tree_py: m2oAny(
                and([
                    condition(complexPath, ">=", DATE_START),
                    condition(complexPath, "<=", DATE_END),
                ])
            ),
        },
        {
            tree_py: and([
                condition(complexPath, ">=", DATE_START),
                condition(complexPath, "<=", DATE_END),
            ]),
        },
        {
            tree_py: m2oAny(
                and([
                    condition(complexPath, ">=", DATE_START),
                    condition(complexPath, "<=", DATE_END),
                ])
            ),
        },
        {
            tree_py: and([
                condition("m2o.dt_2", ">=", DATE_START),
                condition("m2o.dt_2", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("m2o.date_2", ">=", DATE_START),
                condition("m2o.date_2", "<=", DATE_END),
            ]),
        },
    ];
    for (const { tree_py } of toTest) {
        expect(introduceVirtualOperators(tree_py, fullOptions)).toEqual(tree_py);
    }
});

test(`"in range" operator: no introduction if condition negated or "|" or different path (generateSmartDates=false)`, async () => {
    const toTest = [
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START, true),
                condition("date_1", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START),
                condition("date_1", "<=", DATE_END, true),
            ]),
        },
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START, true),
                condition("date_1", "<=", DATE_END, true),
            ]),
        },
        {
            tree_py: or([
                condition("date_1", ">=", DATE_START),
                condition("date_1", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START),
                condition("date_3", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("today"), true),
                condition("dt_1", "<", pyDatetime("days = 1")),
            ]),
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("today")),
                condition("dt_1", "<", pyDatetime("days = 1"), true),
            ]),
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("today"), true),
                condition("dt_1", "<", pyDatetime("days = 1"), true),
            ]),
        },
        {
            tree_py: or([
                condition("dt_1", ">=", pyDatetime("today")),
                condition("dt_1", "<", pyDatetime("days = 1")),
            ]),
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("today")),
                condition("dt_3", "<", pyDatetime("days = 1")),
            ]),
        },
    ];
    for (const { tree_py } of toTest) {
        expect(introduceVirtualOperators(tree_py, fullOptions)).toEqual(tree_py);
    }
});

test(`"in range" operator: introduction/elimination for datetime fields (generateSmartDates=false)`, async () => {
    mockDate("2025-07-03 16:20:00");
    await makeMockEnv();
    const toTest = [
        {
            tree_py: and([condition("dt_1", ">=", DATE_START), condition("dt_1", "<=", DATE_END)]),
            tree: inRange("dt_1", ["datetime", "custom range", DATE_START, DATE_END]),
            domain: ["&", ["dt_1", ">=", DATE_START], ["dt_1", "<=", DATE_END]],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("days = -7")),
                condition("dt_1", "<", pyDatetime("today")),
            ]),
            tree: inRange("dt_1", ["datetime", "last 7 days", false, false]),
            domain: [
                "&",
                ["dt_1", ">=", "2025-06-25 23:00:00"],
                ["dt_1", "<", "2025-07-02 23:00:00"],
            ],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("days = -30")),
                condition("dt_1", "<", pyDatetime("today")),
            ]),
            tree: inRange("dt_1", ["datetime", "last 30 days", false, false]),
            domain: [
                "&",
                ["dt_1", ">=", "2025-06-02 23:00:00"],
                ["dt_1", "<", "2025-07-02 23:00:00"],
            ],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("day = 1")),
                condition("dt_1", "<", pyDatetime("days = 1")),
            ]),
            tree: inRange("dt_1", ["datetime", "month to date", false, false]),
            domain: [
                "&",
                ["dt_1", ">=", "2025-06-30 23:00:00"],
                ["dt_1", "<", "2025-07-03 23:00:00"],
            ],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("day = 1, months = -1")),
                condition("dt_1", "<", pyDatetime("day = 1")),
            ]),
            tree: inRange("dt_1", ["datetime", "last month", false, false]),
            domain: [
                "&",
                ["dt_1", ">=", "2025-05-31 23:00:00"],
                ["dt_1", "<", "2025-06-30 23:00:00"],
            ],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("day = 1, month = 1")),
                condition("dt_1", "<", pyDatetime("days = 1")),
            ]),
            tree: inRange("dt_1", ["datetime", "year to date", false, false]),
            domain: [
                "&",
                ["dt_1", ">=", "2024-12-31 23:00:00"],
                ["dt_1", "<", "2025-07-03 23:00:00"],
            ],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", pyDatetime("day = 1, months = -12")),
                condition("dt_1", "<", pyDatetime("day = 1")),
            ]),
            tree: inRange("dt_1", ["datetime", "last 12 months", false, false]),
            domain: [
                "&",
                ["dt_1", ">=", "2024-06-30 23:00:00"],
                ["dt_1", "<", "2025-06-30 23:00:00"],
            ],
        },
        {
            tree_py: and(
                [condition("dt_1", ">=", DATE_START), condition("dt_1", "<=", DATE_END)],
                true
            ),
            tree: inRange("dt_1", ["datetime", "custom range", DATE_START, DATE_END], true),
            domain: ["!", "&", ["dt_1", ">=", DATE_START], ["dt_1", "<=", DATE_END]],
        },
        {
            tree_py: m2oAny(
                and([condition("dt_2", ">=", DATE_START), condition("dt_2", "<=", DATE_END)])
            ),
            tree: inRange("m2o.dt_2", ["datetime", "custom range", DATE_START, DATE_END]),
            domain: [["m2o", "any", ["&", ["dt_2", ">=", DATE_START], ["dt_2", "<=", DATE_END]]]],
        },
        {
            tree_py: m2oAny(
                and([condition("dt_2", ">=", DATE_START), condition("dt_2", "<=", DATE_END)]),
                true
            ),
            tree: m2oAny(inRange("dt_2", ["datetime", "custom range", DATE_START, DATE_END]), true),
            domain: [
                "!",
                ["m2o", "any", ["&", ["dt_2", ">=", DATE_START], ["dt_2", "<=", DATE_END]]],
            ],
        },
    ];
    for (const { tree_py, tree } of toTest) {
        expect(introduceVirtualOperators(tree_py, fullOptions)).toEqual(tree || tree_py);
        expect(eliminateVirtualOperators(tree || tree_py, fullOptions)).toEqual(tree_py);
    }
    for (const { tree_py, domain } of toTest) {
        expect(new Domain(constructDomainFromTree(tree_py)).toList()).toEqual(domain || []);
    }
});

test(`"in range" operator: introduction/elimination for date fields (generateSmartDates=false)`, async () => {
    mockDate("2025-07-03 16:20:00");
    await makeMockEnv();
    const toTest = [
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START),
                condition("date_1", "<=", DATE_END),
            ]),
            tree: inRange("date_1", ["date", "custom range", DATE_START, DATE_END]),
            domain: ["&", ["date_1", ">=", DATE_START], ["date_1", "<=", DATE_END]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", pyDate("today")),
                condition("date_1", "<", pyDate("days = 1")),
            ]),
            tree: inRange("date_1", ["date", "today", false, false]),
            domain: ["&", ["date_1", ">=", "2025-07-03"], ["date_1", "<", "2025-07-04"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", pyDate("days = -7")),
                condition("date_1", "<", pyDate("today")),
            ]),
            tree: inRange("date_1", ["date", "last 7 days", false, false]),
            domain: ["&", ["date_1", ">=", "2025-06-26"], ["date_1", "<", "2025-07-03"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", pyDate("days = -30")),
                condition("date_1", "<", pyDate("today")),
            ]),
            tree: inRange("date_1", ["date", "last 30 days", false, false]),
            domain: ["&", ["date_1", ">=", "2025-06-03"], ["date_1", "<", "2025-07-03"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", pyDate("day = 1")),
                condition("date_1", "<", pyDate("days = 1")),
            ]),
            tree: inRange("date_1", ["date", "month to date", false, false]),
            domain: ["&", ["date_1", ">=", "2025-07-01"], ["date_1", "<", "2025-07-04"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", pyDate("day = 1, months = -1")),
                condition("date_1", "<", pyDate("day = 1")),
            ]),
            tree: inRange("date_1", ["date", "last month", false, false]),
            domain: ["&", ["date_1", ">=", "2025-06-01"], ["date_1", "<", "2025-07-01"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", pyDate("day = 1, month = 1")),
                condition("date_1", "<", pyDate("days = 1")),
            ]),
            tree: inRange("date_1", ["date", "year to date", false, false]),
            domain: ["&", ["date_1", ">=", "2025-01-01"], ["date_1", "<", "2025-07-04"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", pyDate("day = 1, months = -12")),
                condition("date_1", "<", pyDate("day=1")),
            ]),
            tree: inRange("date_1", ["date", "last 12 months", false, false]),
            domain: ["&", ["date_1", ">=", "2024-07-01"], ["date_1", "<", "2025-07-01"]],
        },
        {
            tree_py: and(
                [condition("date_1", ">=", DATE_START), condition("date_1", "<=", DATE_END)],
                true
            ),
            tree: inRange("date_1", ["date", "custom range", DATE_START, DATE_END], true),
            domain: ["!", "&", ["date_1", ">=", DATE_START], ["date_1", "<=", DATE_END]],
        },
        {
            tree_py: m2oAny(
                and([condition("date_2", ">=", DATE_START), condition("date_2", "<=", DATE_END)])
            ),
            tree: inRange("m2o.date_2", ["date", "custom range", DATE_START, DATE_END]),
            domain: [
                ["m2o", "any", ["&", ["date_2", ">=", DATE_START], ["date_2", "<=", DATE_END]]],
            ],
        },
        {
            tree_py: m2oAny(
                and([condition("date_2", ">=", DATE_START), condition("date_2", "<=", DATE_END)]),
                true
            ),
            tree: m2oAny(inRange("date_2", ["date", "custom range", DATE_START, DATE_END]), true),
            domain: [
                "!",
                ["m2o", "any", ["&", ["date_2", ">=", DATE_START], ["date_2", "<=", DATE_END]]],
            ],
        },
    ];
    for (const { tree_py, tree } of toTest) {
        expect(introduceVirtualOperators(tree_py, fullOptions)).toEqual(tree);
        expect(eliminateVirtualOperators(tree, fullOptions)).toEqual(tree_py);
    }
    for (const { tree_py, domain } of toTest) {
        expect(new Domain(constructDomainFromTree(tree_py)).toList()).toEqual(domain || []);
    }
});

test(`"in range" operator: no introduction for complex paths`, async () => {
    const toTest = [
        {
            tree_py: and([
                condition(complexPath, ">=", DATE_START),
                condition(complexPath, "<=", DATE_END),
            ]),
        },
        {
            tree_py: m2oAny(
                and([
                    condition(complexPath, ">=", DATE_START),
                    condition(complexPath, "<=", DATE_END),
                ])
            ),
        },
        {
            tree_py: and([
                condition(complexPath, ">=", DATE_START),
                condition(complexPath, "<=", DATE_END),
            ]),
        },
        {
            tree_py: m2oAny(
                and([
                    condition(complexPath, ">=", DATE_START),
                    condition(complexPath, "<=", DATE_END),
                ])
            ),
        },
        {
            tree_py: and([
                condition("m2o.dt_2", ">=", DATE_START),
                condition("m2o.dt_2", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("m2o.date_2", ">=", DATE_START),
                condition("m2o.date_2", "<=", DATE_END),
            ]),
        },
    ];
    for (const { tree_py } of toTest) {
        expect(introduceVirtualOperators(tree_py, options)).toEqual(tree_py);
    }
});

test(`"in range" operator: no introduction if condition negated or "|" or different path`, async () => {
    const toTest = [
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START, true),
                condition("date_1", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START),
                condition("date_1", "<=", DATE_END, true),
            ]),
        },
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START, true),
                condition("date_1", "<=", DATE_END, true),
            ]),
        },
        {
            tree_py: or([
                condition("date_1", ">=", DATE_START),
                condition("date_1", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START),
                condition("date_3", "<=", DATE_END),
            ]),
        },
        {
            tree_py: and([
                condition("dt_1", ">=", "today", true),
                condition("dt_1", "<", "today +1d"),
            ]),
        },
        {
            tree_py: and([
                condition("dt_1", ">=", "today"),
                condition("dt_1", "<", "today +1d", true),
            ]),
        },
        {
            tree_py: and([
                condition("dt_1", ">=", "today", true),
                condition("dt_1", "<", "today +1d", true),
            ]),
        },
        {
            tree_py: or([condition("dt_1", ">=", "today"), condition("dt_1", "<", "today +1d")]),
        },
        {
            tree_py: and([condition("dt_1", ">=", "today"), condition("dt_3", "<", "today +1d")]),
        },
    ];
    for (const { tree_py } of toTest) {
        expect(introduceVirtualOperators(tree_py, options)).toEqual(tree_py);
    }
});

test(`"in range" operator: introduction/elimination for datetime fields`, async () => {
    await makeMockEnv();
    const toTest = [
        {
            tree_py: and([condition("dt_1", ">=", DATE_START), condition("dt_1", "<=", DATE_END)]),
            tree: inRange("dt_1", ["datetime", "custom range", DATE_START, DATE_END]),
            domain: ["&", ["dt_1", ">=", DATE_START], ["dt_1", "<=", DATE_END]],
        },
        {
            tree_py: and([condition("dt_1", ">=", "today"), condition("dt_1", "<", "today +1d")]),
            tree: inRange("dt_1", ["datetime", "today", false, false]),
            domain: ["&", ["dt_1", ">=", "today"], ["dt_1", "<", "today +1d"]],
        },
        {
            tree_py: and([condition("dt_1", ">=", "today -7d"), condition("dt_1", "<", "today")]),
            tree: inRange("dt_1", ["datetime", "last 7 days", false, false]),
            domain: ["&", ["dt_1", ">=", "today -7d"], ["dt_1", "<", "today"]],
        },
        {
            tree_py: and([condition("dt_1", ">=", "today -30d"), condition("dt_1", "<", "today")]),
            tree: inRange("dt_1", ["datetime", "last 30 days", false, false]),
            domain: ["&", ["dt_1", ">=", "today -30d"], ["dt_1", "<", "today"]],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", "today =1d"),
                condition("dt_1", "<", "today +1d"),
            ]),
            tree: inRange("dt_1", ["datetime", "month to date", false, false]),
            domain: ["&", ["dt_1", ">=", "today =1d"], ["dt_1", "<", "today +1d"]],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", "today =1d -1m"),
                condition("dt_1", "<", "today =1d"),
            ]),
            tree: inRange("dt_1", ["datetime", "last month", false, false]),
            domain: ["&", ["dt_1", ">=", "today =1d -1m"], ["dt_1", "<", "today =1d"]],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", "today =1m =1d"),
                condition("dt_1", "<", "today +1d"),
            ]),
            tree: inRange("dt_1", ["datetime", "year to date", false, false]),
            domain: ["&", ["dt_1", ">=", "today =1m =1d"], ["dt_1", "<", "today +1d"]],
        },
        {
            tree_py: and([
                condition("dt_1", ">=", "today =1d -12m"),
                condition("dt_1", "<", "today =1d"),
            ]),
            tree: inRange("dt_1", ["datetime", "last 12 months", false, false]),
            domain: ["&", ["dt_1", ">=", "today =1d -12m"], ["dt_1", "<", "today =1d"]],
        },
        {
            tree_py: and(
                [condition("dt_1", ">=", DATE_START), condition("dt_1", "<=", DATE_END)],
                true
            ),
            tree: inRange("dt_1", ["datetime", "custom range", DATE_START, DATE_END], true),
            domain: ["!", "&", ["dt_1", ">=", DATE_START], ["dt_1", "<=", DATE_END]],
        },
        {
            tree_py: m2oAny(
                and([condition("dt_2", ">=", DATE_START), condition("dt_2", "<=", DATE_END)])
            ),
            tree: inRange("m2o.dt_2", ["datetime", "custom range", DATE_START, DATE_END]),
            domain: [["m2o", "any", ["&", ["dt_2", ">=", DATE_START], ["dt_2", "<=", DATE_END]]]],
        },
        {
            tree_py: m2oAny(
                and([condition("dt_2", ">=", DATE_START), condition("dt_2", "<=", DATE_END)]),
                true
            ),
            tree: m2oAny(inRange("dt_2", ["datetime", "custom range", DATE_START, DATE_END]), true),
            domain: [
                "!",
                ["m2o", "any", ["&", ["dt_2", ">=", DATE_START], ["dt_2", "<=", DATE_END]]],
            ],
        },
    ];
    for (const { tree_py, tree } of toTest) {
        expect(introduceVirtualOperators(tree_py, options)).toEqual(tree || tree_py);
        expect(eliminateVirtualOperators(tree || tree_py)).toEqual(tree_py);
    }
    for (const { tree_py, domain } of toTest) {
        expect(new Domain(constructDomainFromTree(tree_py)).toList()).toEqual(domain || []);
    }
});

test(`"in range" operator: introduction/elimination for date fields`, async () => {
    await makeMockEnv();
    const toTest = [
        {
            tree_py: and([
                condition("date_1", ">=", "today"),
                condition("date_1", "<", "today +1d"),
            ]),
            tree: inRange("date_1", ["date", "today", false, false]),
            domain: ["&", ["date_1", ">=", "today"], ["date_1", "<", "today +1d"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", "today -7d"),
                condition("date_1", "<", "today"),
            ]),
            tree: inRange("date_1", ["date", "last 7 days", false, false]),
            domain: ["&", ["date_1", ">=", "today -7d"], ["date_1", "<", "today"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", "today -30d"),
                condition("date_1", "<", "today"),
            ]),
            tree: inRange("date_1", ["date", "last 30 days", false, false]),
            domain: ["&", ["date_1", ">=", "today -30d"], ["date_1", "<", "today"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", "today =1d"),
                condition("date_1", "<", "today +1d"),
            ]),
            tree: inRange("date_1", ["date", "month to date", false, false]),
            domain: ["&", ["date_1", ">=", "today =1d"], ["date_1", "<", "today +1d"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", "today =1d -1m"),
                condition("date_1", "<", "today =1d"),
            ]),
            tree: inRange("date_1", ["date", "last month", false, false]),
            domain: ["&", ["date_1", ">=", "today =1d -1m"], ["date_1", "<", "today =1d"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", "today =1m =1d"),
                condition("date_1", "<", "today +1d"),
            ]),
            tree: inRange("date_1", ["date", "year to date", false, false]),
            domain: ["&", ["date_1", ">=", "today =1m =1d"], ["date_1", "<", "today +1d"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", "today =1d -12m"),
                condition("date_1", "<", "today =1d"),
            ]),
            tree: inRange("date_1", ["date", "last 12 months", false, false]),
            domain: ["&", ["date_1", ">=", "today =1d -12m"], ["date_1", "<", "today =1d"]],
        },
        {
            tree_py: and([
                condition("date_1", ">=", DATE_START),
                condition("date_1", "<=", DATE_END),
            ]),
            tree: inRange("date_1", ["date", "custom range", DATE_START, DATE_END]),
            domain: ["&", ["date_1", ">=", DATE_START], ["date_1", "<=", DATE_END]],
        },
        {
            tree_py: and(
                [condition("date_1", ">=", DATE_START), condition("date_1", "<=", DATE_END)],
                true
            ),
            tree: inRange("date_1", ["date", "custom range", DATE_START, DATE_END], true),
            domain: ["!", "&", ["date_1", ">=", DATE_START], ["date_1", "<=", DATE_END]],
        },
        {
            tree_py: m2oAny(
                and([condition("date_2", ">=", DATE_START), condition("date_2", "<=", DATE_END)])
            ),
            tree: inRange("m2o.date_2", ["date", "custom range", DATE_START, DATE_END]),
            domain: [
                ["m2o", "any", ["&", ["date_2", ">=", DATE_START], ["date_2", "<=", DATE_END]]],
            ],
        },
        {
            tree_py: m2oAny(
                and([condition("date_2", ">=", DATE_START), condition("date_2", "<=", DATE_END)]),
                true
            ),
            tree: m2oAny(inRange("date_2", ["date", "custom range", DATE_START, DATE_END]), true),
            domain: [
                "!",
                ["m2o", "any", ["&", ["date_2", ">=", DATE_START], ["date_2", "<=", DATE_END]]],
            ],
        },
    ];
    for (const { tree_py, tree } of toTest) {
        expect(introduceVirtualOperators(tree_py, options)).toEqual(tree);
        expect(eliminateVirtualOperators(tree)).toEqual(tree_py);
    }
    for (const { tree_py, domain } of toTest) {
        expect(new Domain(constructDomainFromTree(tree_py)).toList()).toEqual(domain || []);
    }
});
