import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineActions,
    defineModels,
    defineWebModels,
    fields,
    getService,
    models,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

class Module extends models.Model {
    name = fields.Char();
    category_id = fields.Many2one({ string: "category", relation: "category" });
    module_type = fields.Selection({
        selection: [
            ["official", "Official"],
            ["industries", "Industries"],
        ],
    });

    _records = [
        {
            id: 1,
            name: "CRM",
            module_type: "official",
        },
        {
            id: 2,
            name: "Rental",
            module_type: "official",
        },
        {
            id: 3,
            name: "Hotel",
            module_type: "industries",
        },
    ];
    _views = {
        list: `<list><field name="name"/></list>`,
        search: `
            <search>
                <searchpanel view_types="list" class="o_apps_searchpanel">
                    <field name="module_type" string="Apps" expand="1"/>
                    <field name="category_id" expand="1"/>
                </searchpanel>
            </search>
        `,
    };
}

class Category extends models.Model {
    name = fields.Char({ string: "Category Name" });

    _records = [
        { id: 6, name: "Sales" },
        { id: 7, name: "Hospitality" },
    ];
}

defineModels([Module, Category]);
defineWebModels();

defineActions([
    {
        id: 1,
        name: "Apps",
        res_model: "module",
        views: [[false, "list"]],
        context: {
            searchpanel_default_module_type: "official",
        },
    },
]);

describe.current.tags("desktop");

test("Apps search panel", async () => {

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);


    expect(`.o_search_panel`).toHaveCount(1);
    expect(`.o_search_panel_section`).toHaveCount(2);
    const firstSection = `.o_search_panel_section:eq(0)`;
    expect(`${firstSection} .o_search_panel_section_header`).toHaveText(/Apps/i);
    expect(`${firstSection} .o_search_panel_category_value`).toHaveCount(3);
    expect(`${firstSection} .o_search_panel_category_value:first-child`).toHaveStyle({display: "none",});
    expect(queryAllTexts`${firstSection} .o_search_panel_category_value`).toEqual([
        "All",
        "Official",
        "Industries",
    ]);
    expect(`${firstSection} .o_search_panel_category_value header.active `).toHaveText("Official");
    expect(`.o_list_table .o_data_row`).toHaveCount(2);

    await contains(".o_search_panel_category_value:nth-child(3) header").click();
    expect(`${firstSection} .o_search_panel_category_value header.active `).toHaveText("Industries");
    expect(`.o_list_table .o_data_row`).toHaveCount(1);

    const secondSection = `.o_search_panel_section:eq(1)`;
    expect(`${secondSection} .o_search_panel_category_value:first-child`).not.toHaveStyle({display: "none",});
    expect(queryAllTexts`${secondSection} .o_search_panel_category_value`).toEqual([
        "All",
        "Sales",
        "Hospitality",
    ]);
});
