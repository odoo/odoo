import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineActions,
    defineModels,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";
import { WebClient } from "@web/webclient/webclient";

const { ResCompany, ResPartner, ResUsers } = webModels;

class Partner extends models.Model {
    _rec_name = "display_name";

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
    ];
    _views = {
        "form,false": `
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
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "list,false": `<tree><field name="display_name"/></tree>`,
        "search,false": `<search/>`,
    };
}

defineModels([Partner, ResCompany, ResPartner, ResUsers]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[1, "kanban"]],
    },
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        mobile_view_mode: "kanban",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [1, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 6,
        xml_id: "action_6",
        name: "Partner",
        res_id: 2,
        res_model: "partner",
        target: "inline",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    },
]);

test.tags("desktop")("rainbowman integrated to webClient", async () => {
    patchWithCleanup(user, { showEffect: true });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_reward").toHaveCount(0);
    getService("effect").add({ type: "rainbow_man", message: "", fadeout: "no" });
    await animationFrame();
    expect(".o_reward").toHaveCount(1);
    expect(".o_kanban_view").toHaveCount(1);
    await contains(".o_kanban_record").click();
    expect(".o_reward").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);
    getService("effect").add({ type: "rainbow_man", message: "", fadeout: "no" });
    await animationFrame();
    expect(".o_reward").toHaveCount(1);
    expect(".o_kanban_view").toHaveCount(1);
    // Do not force rainbow man to destroy on doAction
    // we let it die either after its animation or on user click
    await getService("action").doAction(3);
    expect(".o_reward").toHaveCount(1);
    expect(".o_list_view").toHaveCount(1);
});

test.tags("desktop")("on close with effect from server", async () => {
    patchWithCleanup(user, { showEffect: true });
    onRpc("/web/dataset/call_button", () => {
        return {
            type: "ir.actions.act_window_close",
            effect: {
                type: "rainbow_man",
                message: "button called",
            },
        };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(6);
    await contains("button[name=object]").click();
    expect(".o_reward").toHaveCount(1);
});

test("on close with effect in xml", async () => {
    patchWithCleanup(user, { showEffect: true });

    Partner._views["form,false"] = `
        <form>
            <header>
            <button string="Call method" name="object" type="object"
                effect="{'type': 'rainbow_man', 'message': 'rainBowInXML'}"
            />
            </header>
            <field name="display_name"/>
        </form>`;
    onRpc("/web/dataset/call_button", () => false);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(6);
    await contains("button[name=object]").click();
    expect(".o_reward").toHaveCount(1);
    expect(".o_reward .o_reward_msg_content").toHaveText("rainBowInXML");
});
