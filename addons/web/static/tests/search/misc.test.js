import { describe, expect, test } from "@odoo/hoot";
import {
    defineModels,
    fields,
    getService,
    makeMockEnv,
    models,
} from "@web/../tests/web_test_helpers";
import { facet, useGetDomainFacets } from "@web/search/utils/misc";

class TestModel extends models.Model {
    name = fields.Char();
    char = fields.Char();
    float = fields.Float();
    integer = fields.Integer();
    boolean = fields.Boolean();
    date = fields.Date();
    datetime = fields.Datetime();
    selection = fields.Selection({
        selection: [
            ["1", "One"],
            ["2", "Two"],
        ],
    });
    many2one = fields.Many2one({ relation: "test.model" });

    _records = [
        {
            id: 1,
            name: "Record 1",
            char: "a",
            float: 1.5,
            integer: 1,
            boolean: true,
            date: "2025-04-04",
            datetime: "2025-04-04 00:00:00",
            selection: "1",
            many2one: 2,
        },
        {
            id: 2,
            name: "Record 2",
            char: "b",
            float: 2.5,
            integer: 2,
            boolean: false,
            date: "2025-04-04",
            datetime: "2025-04-04 23:59:59",
            selection: "2",
            many2one: 1,
        },
    ];
}

defineModels([TestModel]);

describe.current.tags("headless");

test("useGetDomainFacets", async () => {
    await makeMockEnv();
    const fieldService = getService("field");
    const nameService = getService("name");
    const getDomainFacets = useGetDomainFacets(fieldService, nameService);

    const toTest = [
        { domain: `[]`, result: [facet("True")] },
        { domain: `[(1, "=", 1)]`, result: [facet(1, "1")] },
        { domain: `[(0, "=", 1)]`, result: [facet(1, "0")] },
        {
            domain: `[("char", "=", "a")]`,
            result: [facet("a", "Char")],
        },
        {
            domain: `[("char", "=", False)]`,
            result: [facet("not set", "Char")],
        },
        {
            domain: `[("char", "!=", False)]`,
            result: [facet("set", "Char")],
        },
        {
            domain: `[("integer", "=", 1)]`,
            result: [facet(1, "Integer")],
        },
        {
            domain: `[("float", "=", 1.5)]`,
            result: [facet(1.5, "Float")],
        },
        {
            domain: `[("boolean", "=", False)]`,
            result: [facet("not set", "Boolean")],
        },
        {
            domain: `[("boolean", "!=", False)]`,
            result: [facet("set", "Boolean")],
        },
        {
            domain: `[("boolean", "=", True)]`,
            result: [facet("set", "Boolean")],
        },
        {
            domain: `[("boolean", "!=", True)]`,
            result: [facet("not set", "Boolean")],
        },
        {
            domain: `[("many2one", "=", 1)]`,
            result: [facet("Record 1", "Many2one")],
        },
        {
            domain: `[("many2one.many2one", "=", 1)]`,
            result: [facet("Record 1", "Many2one")],
        },
        {
            domain: `[("date", "=", "2025-04-04")]`,
            result: [facet("04/04/2025", "Date")],
        },
        {
            domain: `[("datetime", "=", "2025-04-04 00:00:00")]`,
            result: [facet("04/04/2025 01:00:00", "Datetime")],
        },
        {
            domain: `[("selection", "=", "1")]`,
            result: [facet("One", "Selection")],
        },
        {
            domain: `["&", ("char", "=", "a"), ("char", "=", False)]`,
            result: [facet("Char")],
        },
        {
            domain: `["|", ("char", "=", "a"), ("char", "=", "b")]`,
            result: [facet(["a", "b"], "Char")],
        },
        {
            domain: `["|", ("char", "=", "a"), ("char", "=", False)]`, // = False => virtual operator not_set
            result: [facet("Char")],
        },
        {
            domain: `["&", ("char", "=", "a"), ("boolean", "=", False)]`,
            options: { splitAndConnector: true },
            result: [facet("a", "Char"), facet("not set", "Boolean")],
        },
        {
            domain: `["&", "&", ("char", "=", "a"), ("char", "=", "b"), ("integer", "=", 1)]`,
            options: { splitAndConnector: true },
            result: [facet("Char"), facet(1, "Integer")],
        },
        {
            domain: `["!", "&", ("char", "=", "a"), ("boolean", "=", False)]`,
            options: { splitAndConnector: true },
            result: [facet("Custom filter")],
        },
        {
            domain: `["|", ("char", "=", "a"), ("boolean", "=", False)]`,
            options: { splitAndConnector: true },
            result: [facet("Custom filter")],
        },
        {
            domain: `["!", "|", ("char", "=", "a"), ("boolean", "=", False)]`,
            options: { splitAndConnector: true },
            result: [facet("a", "Char"), facet("set", "Boolean")],
        },
        {
            domain: `["&", ("char", "=", "a"), ("boolean", "=", False)]`,
            result: [facet("Custom filter")],
        },
        {
            domain: `[("many2one", "=", 1)]`,
            result: [facet("Record 1", "Many2one")],
        },
        {
            domain: `[("many2one", "in", [1, 2])]`,
            result: [facet(["Record 1", "Record 2"], "Many2one")],
        },
        {
            domain: `["&", ("integer", ">=", 1), ("integer", "<=", 2)]`,
            result: [facet("( 1 and 2 )", "Integer")],
        },
        {
            domain: `[("many2one", "any", [])]`,
            result: [facet("Many2one")],
        },
        {
            domain: `[("boolean", "in", [True, False])]`,
            result: [facet([true, false], "Boolean")],
        },
        {
            domain: `["&", ("char", ">=", "l"), ("char", "<=", "t")]`,
            result: [facet(["( l and t )"], "Char")],
        },
        {
            domain: `["&", ("date", ">=", (context_today() + relativedelta(months = -1)).strftime("%Y-%m-%d")), ("date", "<=", context_today().strftime("%Y-%m-%d"))]`,
            result: [facet(["1 months"], "Date")],
        },
    ];

    for (const { domain, options, result } of toTest) {
        const facets = await getDomainFacets("test.model", domain, options);
        expect(facets).toEqual(result);
    }
});
