/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Board", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();

        serverData = {
            models: {
                board: {
                    fields: {},
                    records: [],
                },
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                        },
                    ],
                },
            },
            views: {
                "partner,100000001,form": "<form/>",
                "partner,100000002,search": "<search/>",
            },
        };
        setupViewRegistries();
    });

    QUnit.module("BoardView");

    QUnit.test("can't switch views in the dashboard", async (assert) => {
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "list"]],
                    });
                }
            },
        });

        assert.containsNone(target, ".o-dashboard-header", "Couldn't allow user to Change layout");
        assert.containsOnce(target, ".o-dashboard-layout-1", "The display layout is force to 1");
        assert.isNotVisible(
            target.querySelector(".o-dashboard-action .o_control_panel"),
            "views in the dashboard do not have a control panel"
        );
        assert.containsNone(
            target,
            ".o-dashboard-action-header .fa-close",
            "Should not have a close action button"
        );
    });

    QUnit.test("Correctly soft switch to '1' layout on small screen", async function (assert) {
        serverData.views["partner,4,list"] = '<tree string="Partner"><field name="foo"/></tree>';

        await makeView({
            serverData,
            type: "form",
            resModel: "board",
            arch: `
                <form string="My Dashboard" js_class="board">
                    <board style="2-1">
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                        <column>
                            <action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[['foo', '!=', 'False']]"></action>
                        </column>
                    </board>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [[4, "list"]],
                    });
                }
            },
        });
        assert.containsOnce(target, ".o-dashboard-layout-1", "The display layout is force to 1");
        assert.containsOnce(
            target,
            ".o-dashboard-column",
            "The display layout is force to 1 column"
        );
        assert.containsN(
            target,
            ".o-dashboard-action",
            2,
            "The display should contains the 2 actions"
        );
    });
});
