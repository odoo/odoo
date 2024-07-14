/** @odoo-module **/

import {
    createWebClient,
    doAction,
    getActionManagerServerData,
    loadState,
} from "@web/../tests/webclient/helpers";
import { click, getFixture } from "@web/../tests/helpers/utils";

let serverData;
let target;

QUnit.module("ActionManager", {
    beforeEach() {
        serverData = getActionManagerServerData();
        target = getFixture();
        Object.assign(serverData, {
            actions: {
                1: {
                    id: 1,
                    name: "Partners Action 1",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    mobile_view_mode: "kanban",
                    views: [
                        [false, "list"],
                        [false, "kanban"],
                        [false, "form"],
                    ],
                },
                2: {
                    id: 2,
                    name: "Partners Action 2",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                },
            },
            views: {
                "partner,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                "partner,false,list": '<tree><field name="foo"/></tree>',
                "partner,false,form": `<form>
                    <group>
                        <field name="display_name"/>
                    </group>
                </form>`,
                "partner,false,search": '<search><field name="foo" string="Foo"/></search>',
            },
            models: {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                    },
                    records: [{ id: 1, display_name: "First record", foo: "yop" }],
                },
            },
        });
    },
});

QUnit.test("uses a mobile-friendly view by default (if possible)", async function (assert) {
    const webClient = await createWebClient({ serverData });
    // should default on a mobile-friendly view (kanban) for action 1
    await doAction(webClient, 1);

    assert.containsNone(target, ".o_list_view");
    assert.containsOnce(target, ".o_kanban_view");

    // there is no mobile-friendly view for action 2, should use the first one (list)
    await doAction(webClient, 2);

    assert.containsOnce(target, ".o_list_view");
    assert.containsNone(target, ".o_kanban_view");
});

QUnit.test("lazy load mobile-friendly view", async function (assert) {
    const mockRPC = (route, args) => {
        assert.step(args.method || route);
    };

    const webClient = await createWebClient({ serverData, mockRPC });

    await loadState(webClient, {
        action: 1,
        view_type: "form",
    });

    assert.containsNone(target, ".o_list_view");
    assert.containsNone(target, ".o_kanban_view");
    assert.containsOnce(target, ".o_form_view");

    // go back to lazy loaded view
    await click(target, ".o_control_panel .o_breadcrumb .o_back_button");
    assert.containsNone(target, ".o_form_view");
    assert.containsNone(target, ".o_list_view");
    assert.containsOnce(target, ".o_kanban_view");

    assert.verifySteps([
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "onchange", // default_get/onchange to open form view
        "web_search_read", // web search read when coming back to Kanban
    ]);
});

QUnit.test(
    "view switcher button should be displayed in dropdown on mobile screens",
    async function (assert) {
        // This test will spawn a kanban view (mobile friendly).
        // so, the "legacy" code won't be tested here.
        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);

        assert.containsOnce(
            target.querySelector(".o_control_panel"),
            ".o_cp_switch_buttons.d-xl-none > button"
        );
        assert.containsNone(
            target.querySelector(".o_control_panel"),
            ".o_cp_switch_buttons.d-xl-none .o_switch_view.o_kanban"
        );
        assert.containsNone(
            target.querySelector(".o_control_panel"),
            ".o_cp_switch_buttons.d-xl-none button.o_switch_view"
        );

        assert.hasClass(
            target.querySelector(".o_control_panel .o_cp_switch_buttons.d-xl-none > button > i"),
            "oi-view-kanban"
        );
        await click(target, ".o_control_panel .o_cp_switch_buttons.d-xl-none > button");

        assert.hasClass(
            target.querySelector(".o_cp_switch_buttons.d-xl-none .dropdown-item .oi-view-kanban")
                .parentElement,
            "selected"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_cp_switch_buttons.d-xl-none .dropdown-item .oi-view-list")
                .parentElement,
            "selected"
        );
    }
);
