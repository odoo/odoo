import { describe, expect, test } from "@odoo/hoot";

import { makeMockEnv } from "@web/../tests/web_test_helpers";
import { formatDomain } from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";

import {
    condition,
    connector,
    domainFromTree,
    treeFromDomain,
} from "@web/core/tree_editor/condition_tree";

describe.current.tags("headless");

const options = {
    getFieldDef: (name) => {
        if (name === "m2m") {
            return { type: "many2many" };
        }
        if (name === "m2m.datetime_2" || name === "datetime_1") {
            return { type: "datetime" };
        }
        if (name === "m2m.datetime_2.__time" || name === "datetime_1.__time") {
            return { type: "datetime_option" };
        }
        if (name === "m2m.datetime_2.__date" || name === "datetime_1.__date") {
            return { type: "datetime_option" };
        }
        return null;
    },
};

test("datetime options: =", async () => {
    await makeMockEnv();

    const toTest = [
        {
            domain: `["&", "&", ("datetime_1.hour_number", "=", 1), ("datetime_1.minute_number", "=", 15), ("datetime_1.second_number", "=", 24)]`,
            tree: condition("datetime_1.__time", "=", "01:15:24"),
        },
        {
            domain: `["&", "&", ("m2m.datetime_2.hour_number", "=", 1), ("m2m.datetime_2.minute_number", "=", 15), ("m2m.datetime_2.second_number", "=", 24)]`,
            tree: connector("&", [
                condition("m2m.datetime_2.hour_number", "=", 1),
                condition("m2m.datetime_2.minute_number", "=", 15),
                condition("m2m.datetime_2.second_number", "=", 24),
            ]),
        },
        {
            domain: `[("m2m", "any", ["&", "&", ("datetime_2.hour_number", "=", 1), ("datetime_2.minute_number", "=", 15), ("datetime_2.second_number", "=", 24)])]`,
            tree: condition("m2m.datetime_2.__time", "=", "01:15:24"),
        },
        {
            domain: `["!", ("m2m", "any", ["&", "&", ("datetime_2.hour_number", "=", 1), ("datetime_2.minute_number", "=", 15), ("datetime_2.second_number", "=", 24)])]`,
            tree: condition("m2m", "any", condition("datetime_2.__time", "=", "01:15:24"), true),
        },
        {
            domain: `["&", "&", ("datetime_1.year_number", "=", 2025), ("datetime_1.month_number", "=", 6), ("datetime_1.day_of_month", "=", 4)]`,
            tree: condition("datetime_1.__date", "=", "2025-06-04"),
        },
        {
            domain: `["&", "&", ("m2m.datetime_2.year_number", "=", 2025), ("m2m.datetime_2.month_number", "=", 6), ("m2m.datetime_2.day_of_month", "=", 4)]`,
            tree: connector("&", [
                condition("m2m.datetime_2.year_number", "=", 2025),
                condition("m2m.datetime_2.month_number", "=", 6),
                condition("m2m.datetime_2.day_of_month", "=", 4),
            ]),
        },
        {
            domain: `[("m2m", "any", ["&", "&", ("datetime_2.year_number", "=", 2025), ("datetime_2.month_number", "=", 6), ("datetime_2.day_of_month", "=", 4)])]`,
            tree: condition("m2m.datetime_2.__date", "=", "2025-06-04"),
        },
        {
            domain: `["!", ("m2m", "any", ["&", "&", ("datetime_2.year_number", "=", 2025), ("datetime_2.month_number", "=", 6), ("datetime_2.day_of_month", "=", 4)])]`,
            tree: condition("m2m", "any", condition("datetime_2.__date", "=", "2025-06-04"), true),
        },
    ];
    for (const { domain, tree } of toTest) {
        expect(treeFromDomain(domain, options)).toEqual(tree);
        expect(domainFromTree(tree)).toEqual(formatDomain(domain));
    }
});

test("datetime options: !=", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `["|", "|", ("datetime_1.hour_number", "!=", 1), ("datetime_1.minute_number", "!=", 15), ("datetime_1.second_number", "!=", 24)]`,
            tree: condition("datetime_1.__time", "!=", "01:15:24"),
        },
        {
            domain: `["|", "|", ("m2m.datetime_2.hour_number", "!=", 1), ("m2m.datetime_2.minute_number", "!=", 15), ("m2m.datetime_2.second_number", "!=", 24)]`,
            tree: connector("|", [
                condition("m2m.datetime_2.hour_number", "!=", 1),
                condition("m2m.datetime_2.minute_number", "!=", 15),
                condition("m2m.datetime_2.second_number", "!=", 24),
            ]),
        },
        {
            domain: `[("m2m", "any", ["|", "|", ("datetime_2.hour_number", "!=", 1), ("datetime_2.minute_number", "!=", 15), ("datetime_2.second_number", "!=", 24)])]`,
            tree: condition("m2m.datetime_2.__time", "!=", "01:15:24"),
        },
        {
            domain: `["!", ("m2m", "any", ["|", "|", ("datetime_2.hour_number", "!=", 1), ("datetime_2.minute_number", "!=", 15), ("datetime_2.second_number", "!=", 24)])]`,
            tree: condition("m2m", "any", condition("datetime_2.__time", "!=", "01:15:24"), true),
        },
        {
            domain: `["|", "|", ("datetime_1.year_number", "!=", 2025), ("datetime_1.month_number", "!=", 6), ("datetime_1.day_of_month", "!=", 4)]`,
            tree: condition("datetime_1.__date", "!=", "2025-06-04"),
        },
        {
            domain: `["|", "|", ("m2m.datetime_2.year_number", "!=", 2025), ("m2m.datetime_2.month_number", "!=", 6), ("m2m.datetime_2.day_of_month", "!=", 4)]`,
            tree: connector("|", [
                condition("m2m.datetime_2.year_number", "!=", 2025),
                condition("m2m.datetime_2.month_number", "!=", 6),
                condition("m2m.datetime_2.day_of_month", "!=", 4),
            ]),
        },
        {
            domain: `[("m2m", "any", ["|", "|", ("datetime_2.year_number", "!=", 2025), ("datetime_2.month_number", "!=", 6), ("datetime_2.day_of_month", "!=", 4)])]`,
            tree: condition("m2m.datetime_2.__date", "!=", "2025-06-04"),
        },
        {
            domain: `["!", ("m2m", "any", ["|", "|", ("datetime_2.year_number", "!=", 2025), ("datetime_2.month_number", "!=", 6), ("datetime_2.day_of_month", "!=", 4)])]`,
            tree: condition("m2m", "any", condition("datetime_2.__date", "!=", "2025-06-04"), true),
        },
    ];
    for (const { domain, tree } of toTest) {
        expect(treeFromDomain(domain, options)).toEqual(tree);
        expect(domainFromTree(tree)).toEqual(formatDomain(domain));
    }
});

test("datetime options: >", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `[
                "|","|",
                    ("datetime_1.hour_number",">",1),
                    "&",("datetime_1.hour_number","=",1),("datetime_1.minute_number",">",15),
                    "&","&",("datetime_1.hour_number","=",1),("datetime_1.minute_number","=",15),("datetime_1.second_number",">",24)
            ]`,
            tree: condition("datetime_1.__time", ">", "01:15:24"),
        },
        {
            domain: `[
                "|","|",
                    ("m2m.datetime_2.hour_number",">",1),
                    "&",("m2m.datetime_2.hour_number","=",1),("m2m.datetime_2.minute_number",">",15),
                    "&","&",("m2m.datetime_2.hour_number","=",1),("m2m.datetime_2.minute_number","=",15),("m2m.datetime_2.second_number",">",24)
            ]`,
            tree: connector("|", [
                condition("m2m.datetime_2.hour_number", ">", 1),
                connector("&", [
                    condition("m2m.datetime_2.hour_number", "=", 1),
                    condition("m2m.datetime_2.minute_number", ">", 15),
                ]),
                connector("&", [
                    condition("m2m.datetime_2.hour_number", "=", 1),
                    condition("m2m.datetime_2.minute_number", "=", 15),
                    condition("m2m.datetime_2.second_number", ">", 24),
                ]),
            ]),
        },
        {
            domain: `[
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.hour_number",">",1),
                        "&",("datetime_2.hour_number","=",1),("datetime_2.minute_number",">",15),
                        "&","&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","=",15),("datetime_2.second_number",">",24)
                ])
            ]`,
            tree: condition("m2m.datetime_2.__time", ">", "01:15:24"),
        },
        {
            domain: `[
                "!",
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.hour_number",">",1),
                        "&",("datetime_2.hour_number","=",1),("datetime_2.minute_number",">",15),
                        "&","&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","=",15),("datetime_2.second_number",">",24)
                ])
            ]`,
            tree: condition("m2m", "any", condition("datetime_2.__time", ">", "01:15:24"), true),
        },
        {
            domain: `[
                "|","|",
                    ("datetime_1.year_number",">",2025),
                    "&",("datetime_1.year_number","=",2025),("datetime_1.month_number",">",6),
                    "&","&",("datetime_1.year_number","=",2025),("datetime_1.month_number","=",6),("datetime_1.day_of_month",">",4)
            ]`,
            tree: condition("datetime_1.__date", ">", "2025-06-04"),
        },
        {
            domain: `[
                "|","|",
                    ("m2m.datetime_2.year_number",">",2025),
                    "&",("m2m.datetime_2.year_number","=",2025),("m2m.datetime_2.month_number",">",6),
                    "&","&",("m2m.datetime_2.year_number","=",2025),("m2m.datetime_2.month_number","=",6),("m2m.datetime_2.day_of_month",">",4)
            ]`,
            tree: connector("|", [
                condition("m2m.datetime_2.year_number", ">", 2025),
                connector("&", [
                    condition("m2m.datetime_2.year_number", "=", 2025),
                    condition("m2m.datetime_2.month_number", ">", 6),
                ]),
                connector("&", [
                    condition("m2m.datetime_2.year_number", "=", 2025),
                    condition("m2m.datetime_2.month_number", "=", 6),
                    condition("m2m.datetime_2.day_of_month", ">", 4),
                ]),
            ]),
        },
        {
            domain: `[
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.year_number",">",2025),
                        "&",("datetime_2.year_number","=",2025),("datetime_2.month_number",">",6),
                        "&","&",("datetime_2.year_number","=",2025),("datetime_2.month_number","=",6),("datetime_2.day_of_month",">",4)
                ])
            ]`,
            tree: condition("m2m.datetime_2.__date", ">", "2025-06-04"),
        },
        {
            domain: `[
                "!",
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.year_number",">",2025),
                        "&",("datetime_2.year_number","=",2025),("datetime_2.month_number",">",6),
                        "&","&",("datetime_2.year_number","=",2025),("datetime_2.month_number","=",6),("datetime_2.day_of_month",">",4)
                ])
            ]`,
            tree: condition("m2m", "any", condition("datetime_2.__date", ">", "2025-06-04"), true),
        },
    ];
    for (const { domain, tree } of toTest) {
        expect(treeFromDomain(domain, options)).toEqual(tree);
        expect(domainFromTree(tree)).toEqual(formatDomain(domain));
    }
});

test("datetime options: <", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `[
                "|","|",
                    ("datetime_1.hour_number","<",1),
                    "&",("datetime_1.hour_number","=",1),("datetime_1.minute_number","<",15),
                    "&","&",("datetime_1.hour_number","=",1),("datetime_1.minute_number","=",15),("datetime_1.second_number","<",24)
            ]`,
            tree: condition("datetime_1.__time", "<", "01:15:24"),
        },
        {
            domain: `[
                "|","|",
                    ("m2m.datetime_2.hour_number","<",1),
                    "&",("m2m.datetime_2.hour_number","=",1),("m2m.datetime_2.minute_number","<",15),
                    "&","&",("m2m.datetime_2.hour_number","=",1),("m2m.datetime_2.minute_number","=",15),("m2m.datetime_2.second_number","<",24)
            ]`,
            tree: connector("|", [
                condition("m2m.datetime_2.hour_number", "<", 1),
                connector("&", [
                    condition("m2m.datetime_2.hour_number", "=", 1),
                    condition("m2m.datetime_2.minute_number", "<", 15),
                ]),
                connector("&", [
                    condition("m2m.datetime_2.hour_number", "=", 1),
                    condition("m2m.datetime_2.minute_number", "=", 15),
                    condition("m2m.datetime_2.second_number", "<", 24),
                ]),
            ]),
        },
        {
            domain: `[
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.hour_number","<",1),
                        "&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","<",15),
                        "&","&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","=",15),("datetime_2.second_number","<",24)
                ])
            ]`,
            tree: condition("m2m.datetime_2.__time", "<", "01:15:24"),
        },
        {
            domain: `[
                "!",
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.hour_number","<",1),
                        "&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","<",15),
                        "&","&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","=",15),("datetime_2.second_number","<",24)
                ])
            ]`,
            tree: condition("m2m", "any", condition("datetime_2.__time", "<", "01:15:24"), true),
        },
        {
            domain: `[
                "|","|",
                    ("datetime_1.year_number","<",2025),
                    "&",("datetime_1.year_number","=",2025),("datetime_1.month_number","<",6),
                    "&","&",("datetime_1.year_number","=",2025),("datetime_1.month_number","=",6),("datetime_1.day_of_month","<",4)
            ]`,
            tree: condition("datetime_1.__date", "<", "2025-06-04"),
        },
        {
            domain: `[
                "|","|",
                    ("m2m.datetime_2.year_number","<",2025),
                    "&",("m2m.datetime_2.year_number","=",2025),("m2m.datetime_2.month_number","<",6),
                    "&","&",("m2m.datetime_2.year_number","=",2025),("m2m.datetime_2.month_number","=",6),("m2m.datetime_2.day_of_month","<",4)
            ]`,
            tree: connector("|", [
                condition("m2m.datetime_2.year_number", "<", 2025),
                connector("&", [
                    condition("m2m.datetime_2.year_number", "=", 2025),
                    condition("m2m.datetime_2.month_number", "<", 6),
                ]),
                connector("&", [
                    condition("m2m.datetime_2.year_number", "=", 2025),
                    condition("m2m.datetime_2.month_number", "=", 6),
                    condition("m2m.datetime_2.day_of_month", "<", 4),
                ]),
            ]),
        },
        {
            domain: `[
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.year_number","<",2025),
                        "&",("datetime_2.year_number","=",2025),("datetime_2.month_number","<",6),
                        "&","&",("datetime_2.year_number","=",2025),("datetime_2.month_number","=",6),("datetime_2.day_of_month","<",4)
                ])
            ]`,
            tree: condition("m2m.datetime_2.__date", "<", "2025-06-04"),
        },
        {
            domain: `[
                "!",
                ("m2m", "any", [
                    "|","|",
                        ("datetime_2.year_number","<",2025),
                        "&",("datetime_2.year_number","=",2025),("datetime_2.month_number","<",6),
                        "&","&",("datetime_2.year_number","=",2025),("datetime_2.month_number","=",6),("datetime_2.day_of_month","<",4)
                ])
            ]`,
            tree: condition("m2m", "any", condition("datetime_2.__date", "<", "2025-06-04"), true),
        },
    ];
    for (const { domain, tree } of toTest) {
        expect(treeFromDomain(domain, options)).toEqual(tree);
        expect(domainFromTree(tree)).toEqual(formatDomain(domain));
    }
});

test("datetime options: between", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `[
                "&",
                    "|",
                        "|","|",
                            ("datetime_1.hour_number",">",1),
                            "&",("datetime_1.hour_number","=",1),("datetime_1.minute_number",">",15),
                            "&","&",("datetime_1.hour_number","=",1),("datetime_1.minute_number","=",15),("datetime_1.second_number",">",24),
                        "&","&",("datetime_1.hour_number","=",1),("datetime_1.minute_number","=",15),("datetime_1.second_number","=",24),
                    "|",
                        "|","|",
                            ("datetime_1.hour_number","<",22),
                            "&",("datetime_1.hour_number","=",22),("datetime_1.minute_number","<",6),
                            "&","&",("datetime_1.hour_number","=",22),("datetime_1.minute_number","=",6),("datetime_1.second_number","<",56),
                        "&","&",("datetime_1.hour_number","=",22),("datetime_1.minute_number","=",6),("datetime_1.second_number","=",56)
            ]`,
            tree: condition("datetime_1.__time", "between", ["01:15:24", "22:06:56"]),
        },
        {
            domain: `[
                "&",
                    "|",
                        "|","|",
                            ("datetime_1.year_number",">",2025),
                            "&",("datetime_1.year_number","=",2025),("datetime_1.month_number",">",6),
                            "&","&",("datetime_1.year_number","=",2025),("datetime_1.month_number","=",6),("datetime_1.day_of_month",">",4),
                        "&","&",("datetime_1.year_number","=",2025),("datetime_1.month_number","=",6),("datetime_1.day_of_month","=",4),
                    "|",
                        "|","|",
                            ("datetime_1.year_number","<",2026),
                            "&",("datetime_1.year_number","=",2026),("datetime_1.month_number","<",6),
                            "&","&",("datetime_1.year_number","=",2026),("datetime_1.month_number","=",6),("datetime_1.day_of_month","<",27),
                        "&","&",("datetime_1.year_number","=",2026),("datetime_1.month_number","=",6),("datetime_1.day_of_month","=",27)
            ]`,
            tree: condition("datetime_1.__date", "between", ["2025-06-04", "2026-06-27"]),
        },
        {
            domain: `[
                (
                    "m2m",
                    "any",
                    [
                        "&",
                            "|",
                                "|","|",
                                    ("datetime_2.hour_number",">",1),
                                    "&",("datetime_2.hour_number","=",1),("datetime_2.minute_number",">",15),
                                    "&","&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","=",15),("datetime_2.second_number",">",24),
                                "&","&",("datetime_2.hour_number","=",1),("datetime_2.minute_number","=",15),("datetime_2.second_number","=",24),
                            "|",
                                "|","|",
                                    ("datetime_2.hour_number","<",22),
                                    "&",("datetime_2.hour_number","=",22),("datetime_2.minute_number","<",6),
                                    "&","&",("datetime_2.hour_number","=",22),("datetime_2.minute_number","=",6),("datetime_2.second_number","<",56),
                                "&","&",("datetime_2.hour_number","=",22),("datetime_2.minute_number","=",6),("datetime_2.second_number","=",56)
                    ]
                )
            ]`,
            tree: condition("m2m.datetime_2.__time", "between", ["01:15:24", "22:06:56"]),
        },
        {
            domain: `[
                (
                    "m2m",
                    "any",
                    [
                        "&",
                            "|",
                                "|","|",
                                    ("datetime_2.year_number",">",2025),
                                    "&",("datetime_2.year_number","=",2025),("datetime_2.month_number",">",6),
                                    "&","&",("datetime_2.year_number","=",2025),("datetime_2.month_number","=",6),("datetime_2.day_of_month",">",4),
                                "&","&",("datetime_2.year_number","=",2025),("datetime_2.month_number","=",6),("datetime_2.day_of_month","=",4),
                            "|",
                                "|","|",
                                    ("datetime_2.year_number","<",2026),
                                    "&",("datetime_2.year_number","=",2026),("datetime_2.month_number","<",6),
                                    "&","&",("datetime_2.year_number","=",2026),("datetime_2.month_number","=",6),("datetime_2.day_of_month","<",27),
                                "&","&",("datetime_2.year_number","=",2026),("datetime_2.month_number","=",6),("datetime_2.day_of_month","=",27)
                    ]
                )
            ]`,
            tree: condition("m2m.datetime_2.__date", "between", ["2025-06-04", "2026-06-27"]),
        },
    ];
    for (const { domain, tree } of toTest) {
        expect(treeFromDomain(domain, options)).toEqual(tree);
        expect(domainFromTree(tree)).toEqual(formatDomain(domain));
    }
});

test("datetime options: set", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `["|", "|", ("datetime_1.hour_number", "!=", False), ("datetime_1.minute_number", "!=", False), ("datetime_1.second_number", "!=", False)]`,
            tree: condition("datetime_1.__time", "set", false),
        },
        {
            domain: `["|", "|", ("datetime_1.year_number", "!=", False), ("datetime_1.month_number", "!=", False), ("datetime_1.day_of_month", "!=", False)]`,
            tree: condition("datetime_1.__date", "set", false),
        },
    ];
    for (const { domain, tree } of toTest) {
        expect(treeFromDomain(domain, options)).toEqual(tree);
        expect(domainFromTree(tree)).toEqual(formatDomain(domain));
    }
});

test("datetime options: not_set", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `["&", "&", ("datetime_1.hour_number", "=", False), ("datetime_1.minute_number", "=", False), ("datetime_1.second_number", "=", False)]`,
            tree: condition("datetime_1.__time", "not_set", false),
        },
        {
            domain: `["&", "&", ("datetime_1.year_number", "=", False), ("datetime_1.month_number", "=", False), ("datetime_1.day_of_month", "=", False)]`,
            tree: condition("datetime_1.__date", "not_set", false),
        },
    ];
    for (const { domain, tree } of toTest) {
        expect(treeFromDomain(domain, options)).toEqual(tree);
        expect(domainFromTree(tree)).toEqual(formatDomain(domain));
    }
});
