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

describe.current.tags("headless");

const options = {
    getFieldDef: (name) => {
        if (name === "m2o") {
            return { type: "man2one" };
        }
        if (name === "m2o.date_2" || name === "date_1" || name === "date_3") {
            return { type: "date" };
        }
        if (name === "m2o.datetime_2" || name === "datetime_1" || name === "datetime_3") {
            return { type: "datetime" };
        }
        return null;
    },
};

const fullOptions = { ...options, generateSmartDates: false };

test(`"in range" operator: no introduction for complex paths (generateSmartDates=false)`, async () => {
    const toTest = [
        {
            tree_py: connector("&", [
                condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                condition(expression("path"), "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                    condition(expression("path"), "<=", "2025-07-03 00:00:00"),
                ])
            ),
        },
        {
            tree_py: connector("&", [
                condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                condition(expression("path"), "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                    condition(expression("path"), "<=", "2025-07-03 00:00:00"),
                ])
            ),
        },
        {
            tree_py: connector("&", [
                condition("m2o.datetime_2", ">=", "2025-07-02 00:00:00"),
                condition("m2o.datetime_2", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("m2o.date_2", ">=", "2025-07-02 00:00:00"),
                condition("m2o.date_2", "<=", "2025-07-03 00:00:00"),
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
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00", true),
                condition("date_1", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_1", "<=", "2025-07-03 00:00:00", true),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00", true),
                condition("date_1", "<=", "2025-07-03 00:00:00", true),
            ]),
        },
        {
            tree_py: connector("|", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_1", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_3", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    ),
                    true
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    ),
                    true
                ),
            ]),
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    ),
                    true
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    ),
                    true
                ),
            ]),
        },
        {
            tree_py: connector("|", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_3",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
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
            tree_py: connector("&", [
                condition("datetime_1", ">=", "2025-07-02 00:00:00"),
                condition("datetime_1", "<=", "2025-07-03 00:00:00"),
            ]),
            tree: condition("datetime_1", "in range", [
                "datetime",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                "&",
                ["datetime_1", ">=", "2025-07-02 00:00:00"],
                ["datetime_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "today", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2025-07-02 23:00:00"],
                ["datetime_1", "<", "2025-07-03 23:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = -7), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last 7 days", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2025-06-25 23:00:00"],
                ["datetime_1", "<", "2025-07-02 23:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = -30), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last 30 days", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2025-06-02 23:00:00"],
                ["datetime_1", "<", "2025-07-02 23:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(day = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "month to date", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2025-06-30 23:00:00"],
                ["datetime_1", "<", "2025-07-03 23:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(day = 1, months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(day = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last month", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2025-05-31 23:00:00"],
                ["datetime_1", "<", "2025-06-30 23:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(day = 1, month = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "year to date", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2024-12-31 23:00:00"],
                ["datetime_1", "<", "2025-07-03 23:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(day = 1, month = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(days = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "year to date", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2024-12-31 23:00:00"],
                ["datetime_1", "<", "2025-07-03 23:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition(
                    "datetime_1",
                    ">=",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(day = 1, months = -12), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
                condition(
                    "datetime_1",
                    "<",
                    expression(
                        `datetime.datetime.combine(context_today() + relativedelta(day = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
                    )
                ),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last 12 months", false, false]),
            domain: [
                "&",
                ["datetime_1", ">=", "2024-06-30 23:00:00"],
                ["datetime_1", "<", "2025-06-30 23:00:00"],
            ],
        },
        {
            tree_py: connector(
                "&",
                [
                    condition("datetime_1", ">=", "2025-07-02 00:00:00"),
                    condition("datetime_1", "<=", "2025-07-03 00:00:00"),
                ],
                true
            ),
            tree: condition(
                "datetime_1",
                "in range",
                ["datetime", "custom range", "2025-07-02 00:00:00", "2025-07-03 00:00:00"],
                true
            ),
            domain: [
                "!",
                "&",
                ["datetime_1", ">=", "2025-07-02 00:00:00"],
                ["datetime_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("datetime_2", ">=", "2025-07-02 00:00:00"),
                    condition("datetime_2", "<=", "2025-07-03 00:00:00"),
                ])
            ),
            tree: condition("m2o.datetime_2", "in range", [
                "datetime",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["datetime_2", ">=", "2025-07-02 00:00:00"],
                        ["datetime_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("datetime_2", ">=", "2025-07-02 00:00:00"),
                    condition("datetime_2", "<=", "2025-07-03 00:00:00"),
                ]),
                true
            ),
            tree: condition(
                "m2o",
                "any",
                condition("datetime_2", "in range", [
                    "datetime",
                    "custom range",
                    "2025-07-02 00:00:00",
                    "2025-07-03 00:00:00",
                ]),
                true
            ),
            domain: [
                "!",
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["datetime_2", ">=", "2025-07-02 00:00:00"],
                        ["datetime_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
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
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_1", "<=", "2025-07-03 00:00:00"),
            ]),
            tree: condition("date_1", "in range", [
                "date",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                "&",
                ["date_1", ">=", "2025-07-02 00:00:00"],
                ["date_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", expression(`context_today().strftime("%Y-%m-%d")`)),
                condition(
                    "date_1",
                    "<",
                    expression(`(context_today() + relativedelta(days = 1)).strftime('%Y-%m-%d')`)
                ),
            ]),
            tree: condition("date_1", "in range", ["date", "today", false, false]),
            domain: ["&", ["date_1", ">=", "2025-07-03"], ["date_1", "<", "2025-07-04"]],
        },
        {
            tree_py: connector("&", [
                condition(
                    "date_1",
                    ">=",
                    expression(`(context_today() + relativedelta(days = -7)).strftime('%Y-%m-%d')`)
                ),
                condition("date_1", "<", expression(`context_today().strftime("%Y-%m-%d")`)),
            ]),
            tree: condition("date_1", "in range", ["date", "last 7 days", false, false]),
            domain: ["&", ["date_1", ">=", "2025-06-26"], ["date_1", "<", "2025-07-03"]],
        },
        {
            tree_py: connector("&", [
                condition(
                    "date_1",
                    ">=",
                    expression(`(context_today() + relativedelta(days = -30)).strftime('%Y-%m-%d')`)
                ),
                condition("date_1", "<", expression(`context_today().strftime("%Y-%m-%d")`)),
            ]),
            tree: condition("date_1", "in range", ["date", "last 30 days", false, false]),
            domain: ["&", ["date_1", ">=", "2025-06-03"], ["date_1", "<", "2025-07-03"]],
        },
        {
            tree_py: connector("&", [
                condition(
                    "date_1",
                    ">=",
                    expression(`(context_today() + relativedelta(day = 1)).strftime('%Y-%m-%d')`)
                ),
                condition(
                    "date_1",
                    "<",
                    expression(`(context_today() + relativedelta(days = 1)).strftime('%Y-%m-%d')`)
                ),
            ]),
            tree: condition("date_1", "in range", ["date", "month to date", false, false]),
            domain: ["&", ["date_1", ">=", "2025-07-01"], ["date_1", "<", "2025-07-04"]],
        },
        {
            tree_py: connector("&", [
                condition(
                    "date_1",
                    ">=",
                    expression(
                        `(context_today() + relativedelta(day = 1, months = -1)).strftime('%Y-%m-%d')`
                    )
                ),
                condition(
                    "date_1",
                    "<",
                    expression(`(context_today() + relativedelta(day = 1)).strftime('%Y-%m-%d')`)
                ),
            ]),
            tree: condition("date_1", "in range", ["date", "last month", false, false]),
            domain: ["&", ["date_1", ">=", "2025-06-01"], ["date_1", "<", "2025-07-01"]],
        },
        {
            tree_py: connector("&", [
                condition(
                    "date_1",
                    ">=",
                    expression(
                        `(context_today() + relativedelta(day = 1, month = 1)).strftime('%Y-%m-%d')`
                    )
                ),
                condition(
                    "date_1",
                    "<",
                    expression(`(context_today() + relativedelta(days = 1)).strftime('%Y-%m-%d')`)
                ),
            ]),
            tree: condition("date_1", "in range", ["date", "year to date", false, false]),
            domain: ["&", ["date_1", ">=", "2025-01-01"], ["date_1", "<", "2025-07-04"]],
        },
        {
            tree_py: connector("&", [
                condition(
                    "date_1",
                    ">=",
                    expression(
                        `(context_today() + relativedelta(day = 1, month = 1)).strftime('%Y-%m-%d')`
                    )
                ),
                condition(
                    "date_1",
                    "<",
                    expression(`(context_today() + relativedelta(days = 1)).strftime('%Y-%m-%d')`)
                ),
            ]),
            tree: condition("date_1", "in range", ["date", "year to date", false, false]),
            domain: ["&", ["date_1", ">=", "2025-01-01"], ["date_1", "<", "2025-07-04"]],
        },
        {
            tree_py: connector("&", [
                condition(
                    "date_1",
                    ">=",
                    expression(
                        `(context_today() + relativedelta(day = 1, months = -12)).strftime('%Y-%m-%d')`
                    )
                ),
                condition(
                    "date_1",
                    "<",
                    expression(`(context_today() + relativedelta(day = 1)).strftime('%Y-%m-%d')`)
                ),
            ]),
            tree: condition("date_1", "in range", ["date", "last 12 months", false, false]),
            domain: ["&", ["date_1", ">=", "2024-07-01"], ["date_1", "<", "2025-07-01"]],
        },
        {
            tree_py: connector(
                "&",
                [
                    condition("date_1", ">=", "2025-07-02 00:00:00"),
                    condition("date_1", "<=", "2025-07-03 00:00:00"),
                ],
                true
            ),
            tree: condition(
                "date_1",
                "in range",
                ["date", "custom range", "2025-07-02 00:00:00", "2025-07-03 00:00:00"],
                true
            ),
            domain: [
                "!",
                "&",
                ["date_1", ">=", "2025-07-02 00:00:00"],
                ["date_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("date_2", ">=", "2025-07-02 00:00:00"),
                    condition("date_2", "<=", "2025-07-03 00:00:00"),
                ])
            ),
            tree: condition("m2o.date_2", "in range", [
                "date",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["date_2", ">=", "2025-07-02 00:00:00"],
                        ["date_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("date_2", ">=", "2025-07-02 00:00:00"),
                    condition("date_2", "<=", "2025-07-03 00:00:00"),
                ]),
                true
            ),
            tree: condition(
                "m2o",
                "any",
                condition("date_2", "in range", [
                    "date",
                    "custom range",
                    "2025-07-02 00:00:00",
                    "2025-07-03 00:00:00",
                ]),
                true
            ),
            domain: [
                "!",
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["date_2", ">=", "2025-07-02 00:00:00"],
                        ["date_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
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
            tree_py: connector("&", [
                condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                condition(expression("path"), "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                    condition(expression("path"), "<=", "2025-07-03 00:00:00"),
                ])
            ),
        },
        {
            tree_py: connector("&", [
                condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                condition(expression("path"), "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition(expression("path"), ">=", "2025-07-02 00:00:00"),
                    condition(expression("path"), "<=", "2025-07-03 00:00:00"),
                ])
            ),
        },
        {
            tree_py: connector("&", [
                condition("m2o.datetime_2", ">=", "2025-07-02 00:00:00"),
                condition("m2o.datetime_2", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("m2o.date_2", ">=", "2025-07-02 00:00:00"),
                condition("m2o.date_2", "<=", "2025-07-03 00:00:00"),
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
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00", true),
                condition("date_1", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_1", "<=", "2025-07-03 00:00:00", true),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00", true),
                condition("date_1", "<=", "2025-07-03 00:00:00", true),
            ]),
        },
        {
            tree_py: connector("|", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_1", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_3", "<=", "2025-07-03 00:00:00"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today", true),
                condition("datetime_1", "<", "today +1d"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today"),
                condition("datetime_1", "<", "today +1d", true),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today", true),
                condition("datetime_1", "<", "today +1d", true),
            ]),
        },
        {
            tree_py: connector("|", [
                condition("datetime_1", ">=", "today"),
                condition("datetime_1", "<", "today +1d"),
            ]),
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today"),
                condition("datetime_3", "<", "today +1d"),
            ]),
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
            tree_py: connector("&", [
                condition("datetime_1", ">=", "2025-07-02 00:00:00"),
                condition("datetime_1", "<=", "2025-07-03 00:00:00"),
            ]),
            tree: condition("datetime_1", "in range", [
                "datetime",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                "&",
                ["datetime_1", ">=", "2025-07-02 00:00:00"],
                ["datetime_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today"),
                condition("datetime_1", "<", "today +1d"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "today", false, false]),
            domain: ["&", ["datetime_1", ">=", "today"], ["datetime_1", "<", "today +1d"]],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today -7d"),
                condition("datetime_1", "<", "today"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last 7 days", false, false]),
            domain: ["&", ["datetime_1", ">=", "today -7d"], ["datetime_1", "<", "today"]],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today -30d"),
                condition("datetime_1", "<", "today"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last 30 days", false, false]),
            domain: ["&", ["datetime_1", ">=", "today -30d"], ["datetime_1", "<", "today"]],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today =1d"),
                condition("datetime_1", "<", "today +1d"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "month to date", false, false]),
            domain: ["&", ["datetime_1", ">=", "today =1d"], ["datetime_1", "<", "today +1d"]],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today =1d -1m"),
                condition("datetime_1", "<", "today =1d"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last month", false, false]),
            domain: ["&", ["datetime_1", ">=", "today =1d -1m"], ["datetime_1", "<", "today =1d"]],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today =1m =1d"),
                condition("datetime_1", "<", "today +1d"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "year to date", false, false]),
            domain: ["&", ["datetime_1", ">=", "today =1m =1d"], ["datetime_1", "<", "today +1d"]],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today =1m =1d"),
                condition("datetime_1", "<", "today +1d"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "year to date", false, false]),
            domain: ["&", ["datetime_1", ">=", "today =1m =1d"], ["datetime_1", "<", "today +1d"]],
        },
        {
            tree_py: connector("&", [
                condition("datetime_1", ">=", "today =1d -12m"),
                condition("datetime_1", "<", "today =1d"),
            ]),
            tree: condition("datetime_1", "in range", ["datetime", "last 12 months", false, false]),
            domain: ["&", ["datetime_1", ">=", "today =1d -12m"], ["datetime_1", "<", "today =1d"]],
        },
        {
            tree_py: connector(
                "&",
                [
                    condition("datetime_1", ">=", "2025-07-02 00:00:00"),
                    condition("datetime_1", "<=", "2025-07-03 00:00:00"),
                ],
                true
            ),
            tree: condition(
                "datetime_1",
                "in range",
                ["datetime", "custom range", "2025-07-02 00:00:00", "2025-07-03 00:00:00"],
                true
            ),
            domain: [
                "!",
                "&",
                ["datetime_1", ">=", "2025-07-02 00:00:00"],
                ["datetime_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("datetime_2", ">=", "2025-07-02 00:00:00"),
                    condition("datetime_2", "<=", "2025-07-03 00:00:00"),
                ])
            ),
            tree: condition("m2o.datetime_2", "in range", [
                "datetime",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["datetime_2", ">=", "2025-07-02 00:00:00"],
                        ["datetime_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("datetime_2", ">=", "2025-07-02 00:00:00"),
                    condition("datetime_2", "<=", "2025-07-03 00:00:00"),
                ]),
                true
            ),
            tree: condition(
                "m2o",
                "any",
                condition("datetime_2", "in range", [
                    "datetime",
                    "custom range",
                    "2025-07-02 00:00:00",
                    "2025-07-03 00:00:00",
                ]),
                true
            ),
            domain: [
                "!",
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["datetime_2", ">=", "2025-07-02 00:00:00"],
                        ["datetime_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
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
            tree_py: connector("&", [
                condition("date_1", ">=", "2025-07-02 00:00:00"),
                condition("date_1", "<=", "2025-07-03 00:00:00"),
            ]),
            tree: condition("date_1", "in range", [
                "date",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                "&",
                ["date_1", ">=", "2025-07-02 00:00:00"],
                ["date_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "today"),
                condition("date_1", "<", "today +1d"),
            ]),
            tree: condition("date_1", "in range", ["date", "today", false, false]),
            domain: ["&", ["date_1", ">=", "today"], ["date_1", "<", "today +1d"]],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "today -7d"),
                condition("date_1", "<", "today"),
            ]),
            tree: condition("date_1", "in range", ["date", "last 7 days", false, false]),
            domain: ["&", ["date_1", ">=", "today -7d"], ["date_1", "<", "today"]],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "today -30d"),
                condition("date_1", "<", "today"),
            ]),
            tree: condition("date_1", "in range", ["date", "last 30 days", false, false]),
            domain: ["&", ["date_1", ">=", "today -30d"], ["date_1", "<", "today"]],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "today =1d"),
                condition("date_1", "<", "today +1d"),
            ]),
            tree: condition("date_1", "in range", ["date", "month to date", false, false]),
            domain: ["&", ["date_1", ">=", "today =1d"], ["date_1", "<", "today +1d"]],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "today =1d -1m"),
                condition("date_1", "<", "today =1d"),
            ]),
            tree: condition("date_1", "in range", ["date", "last month", false, false]),
            domain: ["&", ["date_1", ">=", "today =1d -1m"], ["date_1", "<", "today =1d"]],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "today =1m =1d"),
                condition("date_1", "<", "today +1d"),
            ]),
            tree: condition("date_1", "in range", ["date", "year to date", false, false]),
            domain: ["&", ["date_1", ">=", "today =1m =1d"], ["date_1", "<", "today +1d"]],
        },
        {
            tree_py: connector("&", [
                condition("date_1", ">=", "today =1d -12m"),
                condition("date_1", "<", "today =1d"),
            ]),
            tree: condition("date_1", "in range", ["date", "last 12 months", false, false]),
            domain: ["&", ["date_1", ">=", "today =1d -12m"], ["date_1", "<", "today =1d"]],
        },
        {
            tree_py: connector(
                "&",
                [
                    condition("date_1", ">=", "2025-07-02 00:00:00"),
                    condition("date_1", "<=", "2025-07-03 00:00:00"),
                ],
                true
            ),
            tree: condition(
                "date_1",
                "in range",
                ["date", "custom range", "2025-07-02 00:00:00", "2025-07-03 00:00:00"],
                true
            ),
            domain: [
                "!",
                "&",
                ["date_1", ">=", "2025-07-02 00:00:00"],
                ["date_1", "<=", "2025-07-03 00:00:00"],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("date_2", ">=", "2025-07-02 00:00:00"),
                    condition("date_2", "<=", "2025-07-03 00:00:00"),
                ])
            ),
            tree: condition("m2o.date_2", "in range", [
                "date",
                "custom range",
                "2025-07-02 00:00:00",
                "2025-07-03 00:00:00",
            ]),
            domain: [
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["date_2", ">=", "2025-07-02 00:00:00"],
                        ["date_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
            ],
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition("date_2", ">=", "2025-07-02 00:00:00"),
                    condition("date_2", "<=", "2025-07-03 00:00:00"),
                ]),
                true
            ),
            tree: condition(
                "m2o",
                "any",
                condition("date_2", "in range", [
                    "date",
                    "custom range",
                    "2025-07-02 00:00:00",
                    "2025-07-03 00:00:00",
                ]),
                true
            ),
            domain: [
                "!",
                [
                    "m2o",
                    "any",
                    [
                        "&",
                        ["date_2", ">=", "2025-07-02 00:00:00"],
                        ["date_2", "<=", "2025-07-03 00:00:00"],
                    ],
                ],
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
