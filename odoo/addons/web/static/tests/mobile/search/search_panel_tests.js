/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { makeWithSearch, setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

import { Component, xml } from "@odoo/owl";

let serverData;
let target;

QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        setupControlPanelServiceRegistry();
        target = getFixture();
        registry.category("services").add("ui", uiService);

        serverData = {
            models: {
                foo: {
                    fields: {
                        tag_id: {
                            string: "Many2One",
                            type: "many2one",
                            relation: "tag",
                            store: true,
                            sortable: true,
                        },
                    },
                    records: [
                        { id: 1, tag_id: 2 },
                        { id: 2, tag_id: 1 },
                        { id: 3, tag_id: 1 },
                    ],
                },
                tag: {
                    fields: {
                        name: { string: "Name", type: "string" },
                    },
                    records: [
                        { id: 1, name: "Gold" },
                        { id: 2, name: "Silver" },
                    ],
                },
            },
        };
    });

    QUnit.module("Search Panel (mobile)");

    QUnit.test("basic search panel rendering", async (assert) => {
        class Parent extends Component {}
        Parent.components = { SearchPanel };
        Parent.template = xml`<SearchPanel/>`;
        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: Parent,
            searchViewFields: serverData.models.foo.fields,
            searchViewArch: `
                <search>
                    <searchpanel>
                        <field name="tag_id" icon="fa-bars" string="Tags"/>
                    </searchpanel>
                </search>`,
        });
        assert.containsOnce(target, ".o_search_panel.o_search_panel_summary");

        await click(target, ".o_search_panel .o_search_panel_current_selection");
        assert.containsOnce(document.body, ".o_search_panel.o_mobile_search");
        assert.containsN(document.body, ".o_search_panel_category_value", 3); // All, Gold, Silver
    });
});
