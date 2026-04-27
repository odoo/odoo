import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineActions,
    defineModels,
    getService,
    fields,
    models,
    mountWithCleanup,
    onRpc,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";

import { redirect } from "@web/core/utils/urls";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

class Partner extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "First record" },
        { id: 2, name: "Second record" },
    ];
    _views = {
        form: `
            <form>
                <group>
                    <field name="name"/>
                </group>
            </form>
        `,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `<list><field name="name"/></list>`,
    };
}

defineModels([Partner]);

defineActions([
    {
        id: 1,
        name: "Partners Action 1",
        res_model: "partner",
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 2,
        name: "Partners Action 2",
        res_model: "partner",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    },
]);

describe.current.tags("mobile");

test("uses a mobile-friendly view by default (if possible)", async () => {
    onRpc("has_group", () => true);

    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();
    // should default on a mobile-friendly view (kanban) for action 1
    await getService("action").doAction(1);

    expect(".o_list_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);

    // there is no mobile-friendly view for action 2, should use the first one (list)
    await getService("action").doAction(2);

    expect(".o_list_view").toHaveCount(1);
    expect(".o_kanban_view").toHaveCount(0);
});

test("lazy load mobile-friendly view", async () => {
    stepAllNetworkCalls();

    redirect("/odoo/action-1/new");
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    expect(".o_list_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(1);

    // go back to lazy loaded view
    await click(".o_breadcrumb .o_back_button");
    await animationFrame();
    expect(".o_list_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "onchange", // default_get/onchange to open form view
        "web_search_read", // web search read when coming back to Kanban
    ]);
});

test("lazy load mobile-friendly view; legacy url", async () => {
    stepAllNetworkCalls();

    redirect("/web#action=1&view_type=form");
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    expect(".o_list_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(1);

    // go back to lazy loaded view
    await click(".o_breadcrumb .o_back_button");
    await animationFrame();
    expect(".o_list_view").toHaveCount(0);
    expect(".o_form_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "onchange", // default_get/onchange to open form view
        "web_search_read", // web search read when coming back to Kanban
    ]);
});

test("view switcher button should be displayed in dropdown on mobile screens", async () => {
    // This test will spawn a kanban view (mobile friendly).
    // so, the "legacy" code won't be tested here.
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    await getService("action").doAction(1);

    expect(".o_control_panel .o_cp_switch_buttons > button").toHaveCount(1);
    expect(".o_control_panel .o_cp_switch_buttons .o_switch_view.o_kanban").toHaveCount(0);
    expect(".o_control_panel .o_cp_switch_buttons button.o_switch_view").toHaveCount(0);

    expect(".o_control_panel .o_cp_switch_buttons > button > i").toHaveClass("oi-view-kanban");
    await click(".o_control_panel .o_cp_switch_buttons > button");
    await animationFrame();

    expect(".dropdown-item:has(.oi-view-kanban)").toHaveClass("selected");
    expect(".dropdown-item:has(.oi-view-list)").not.toHaveClass("selected");
});
