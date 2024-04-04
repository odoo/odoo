import { expect, test } from "@odoo/hoot";
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
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "search,false": `<search/>`,
    };
}

defineModels([Partner]);

test("can execute server actions from db ID", async () => {
    defineActions([
        {
            id: 2,
            type: "ir.actions.server",
            state: "code",
            code: () => {
                return {
                    xml_id: "action_1",
                    name: "Partners Action 1",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[1, "kanban"]],
                };
            },
        },
    ]);

    stepAllNetworkCalls();
    onRpc("/web/action/load", async (request) => {
        const { params } = await request.json();
        expect(params.action_id).toBe(2);
        expect(params.context).toEqual({
            // user context
            lang: "en",
            tz: "taht",
            uid: 7,
            allowed_company_ids: [1],
            // action context
            someKey: 44,
        });
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2, { additionalContext: { someKey: 44 } });
    expect(".o_control_panel").toHaveCount(1, { message: "should have rendered a control panel" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should have rendered a kanban view" });
    expect([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]).toVerifySteps();
});

test("action with html help returned by a server action", async () => {
    defineActions([
        {
            id: 2,
            type: "ir.actions.server",
            state: "code",
            code: () => {
                return {
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "kanban"]],
                    help: "<p>I am not a helper</p>",
                    domain: [[0, "=", 1]],
                };
            },
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);

    expect(".o_kanban_view .o_nocontent_help p").toHaveText("I am not a helper");
});
