import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineActions,
    defineModels,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";

import { WebClient } from "@web/webclient/webclient";

class Partner extends models.Model {
    _rec_name = "display_name";

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
    ];
    _views = {
        form: `
        <form>
            <header>
                <button name="object" string="Call method" type="object"/>
                <button name="4" string="Execute action" type="action"/>
            </header>
            <group>
                <field name="display_name"/>
            </group>
        </form>`,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
    };
}

class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}

defineModels([Partner, User]);

test("can execute server actions from db ID", async () => {
    defineActions([
        {
            id: 2,
            type: "ir.actions.server",
        },
        {
            id: 1,
            xml_id: "action_1",
            name: "Partners Action 1",
            res_model: "partner",
            views: [[1, "kanban"]],
        },
    ]);
    onRpc(
        "/web/action/run",
        async () => 1 // execute action 1
    );
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2, { additionalContext: { someKey: 44 } });
    expect(".o_control_panel").toHaveCount(1, { message: "should have rendered a control panel" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should have rendered a kanban view" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/web/action/run",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

test("handle server actions returning false", async function (assert) {
    defineActions([
        {
            id: 2,
            type: "ir.actions.server",
        },
        {
            id: 5,
            xml_id: "action_5",
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            views: [[false, "form"]],
        },
    ]);
    onRpc("/web/action/run", async () => false);
    stepAllNetworkCalls();
    await mountWithCleanup(WebClient);
    // execute an action in target="new"
    function onClose() {
        expect.step("close handler");
    }
    await getService("action").doAction(5, { onClose });
    expect(".o_technical_modal .o_form_view").toHaveCount(1, {
        message: "should have rendered a form view in a modal",
    });

    // execute a server action that returns false
    await getService("action").doAction(2);
    await animationFrame();
    expect(".o_technical_modal").toHaveCount(0, { message: "should have closed the modal" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "onchange",
        "/web/action/load",
        "/web/action/run",
        "close handler",
    ]);
});

test("action with html help returned by a server action", async () => {
    defineActions([
        {
            id: 2,
            type: "ir.actions.server",
        },
    ]);
    onRpc("/web/action/run", async () => ({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
        help: "<p>I am not a helper</p>",
        domain: [[0, "=", 1]],
    }));

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);

    expect(".o_kanban_view .o_nocontent_help p").toHaveText("I am not a helper");
});
