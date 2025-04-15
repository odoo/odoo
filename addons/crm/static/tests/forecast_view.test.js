import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

class Foo extends models.Model {
    date_field = fields.Date({ store: true, sortable: true });
    bar = fields.Many2one({ store: true, relation: "partner", sortable: true });
    value = fields.Float({ store: true, sortable: true });
    number = fields.Integer({ store: true, sortable: true });

    _views = {
        "graph,1": `<graph js_class="forecast_graph"/>`,
    };
}

class Partner extends models.Model {}

defineModels([Foo, Partner]);
defineMailModels();

const forecastDomain = (forecastStart) => [
    "|",
    ["date_field", "=", false],
    ["date_field", ">=", forecastStart],
];

test("Forecast graph view", async () => {
    expect.assertions(5);
    mockDate("2021-09-16 16:54:00");

    const expectedDomains = [
        forecastDomain("2021-09-01"), // month granularity due to no groupby
        forecastDomain("2021-09-16"), // day granularity due to simple bar groupby
        // quarter granularity due to date field groupby activated with quarter interval option
        forecastDomain("2021-07-01"),
        // quarter granularity due to date field groupby activated with quarter and year interval option
        forecastDomain("2021-01-01"),
        // forecast filter no more active
        [],
    ];

    onRpc("formatted_read_group", ({ kwargs }) => {
        expect(kwargs.domain).toEqual(expectedDomains.shift());
    });
    await mountView({
        resModel: "foo",
        viewId: 1,
        type: "graph",
        searchViewArch: `
            <search>
                <filter name="forecast_filter" string="Forecast Filter" context="{ 'forecast_filter': 1 }"/>
                <filter name="group_by_bar" string="Bar" context="{ 'group_by': 'bar' }"/>
                <filter name="group_by_date_field" string="Date Field" context="{ 'group_by': 'date_field' }"/>
            </search>
        `,
        context: {
            search_default_forecast_filter: 1,
            forecast_field: "date_field",
        },
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Bar");

    await toggleMenuItem("Date Field");
    await toggleMenuItemOption("Date Field", "Quarter");

    await toggleMenuItemOption("Date Field", "Year");

    await toggleMenuItem("Forecast Filter");
});

test("forecast filter domain is combined with other domains following the same rules as other filters (OR in same group, AND between groups)", async () => {
    expect.assertions(1);
    mockDate("2021-09-16 16:54:00");

    onRpc("formatted_read_group", ({ kwargs }) => {
        expect(kwargs.domain).toEqual([
            "&",
            ["number", ">", 2],
            "|",
            ["bar", "=", 2],
            "&",
            ["value", ">", 0.0],
            "|",
            ["date_field", "=", false],
            ["date_field", ">=", "2021-09-01"],
        ]);
    });
    await mountView({
        resModel: "foo",
        type: "graph",
        viewId: 1,
        searchViewArch: `
            <search>
                <filter name="other_group_filter" string="Other Group Filter" domain="[('number', '>', 2)]"/>
                <separator/>
                <filter name="same_group_filter" string="Same Group Filter" domain="[('bar', '=', 2)]"/>
                <filter name="forecast_filter" string="Forecast Filter" context="{ 'forecast_filter': 1 }" domain="[('value', '>', 0.0)]"/>
            </search>
        `,
        context: {
            search_default_same_group_filter: 1,
            search_default_forecast_filter: 1,
            search_default_other_group_filter: 1,
            forecast_field: "date_field",
        },
    });
});
