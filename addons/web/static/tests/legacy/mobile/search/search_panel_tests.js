/** @odoo-module alias=@web/../tests/mobile/search/search_panel_tests default=false */

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
        class Parent extends Component {
            static components = { SearchPanel };
            static template = xml`<SearchPanel/>`;
            static props = ["*"];
        }
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
        assert.containsOnce(target, ".o_search_panel .o-dropdown");
        assert.strictEqual(target.querySelector(".o_search_panel .o-dropdown").innerText, "Tags");

        await click(target, ".o_search_panel .o-dropdown");
        assert.containsOnce(
            document.body,
            ".o_search_panel_section.o_search_panel_category"
        );
        assert.containsN(target, ".o_search_panel_category_value", 3);
        assert.strictEqual(target.querySelector(".o_search_panel_field").innerText, "All\nGold\nSilver");
        await click(target, ".o_search_panel_category_value:nth-of-type(2) header");
        assert.strictEqual(target.querySelector(".o_search_panel .o-dropdown").innerText, "Gold");
        assert.containsOnce(target, ".o_search_panel a");
        await click(target, ".o_search_panel a");
        assert.strictEqual(target.querySelector(".o_search_panel .o-dropdown").innerText, "Tags");
    });
});
