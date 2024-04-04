import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    webModels,
} from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";

const actionRegistry = registry.category("actions");

const { ResCompany, ResPartner, ResUsers } = webModels;

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
]);

test("error in a client action (at rendering)", async () => {
    expect.assertions(9);
    class Boom extends Component {
        static template = xml`<div><t t-esc="a.b.c"/></div>`;
        static props = ["*"];
    }
    actionRegistry.add("Boom", Boom);
    onRpc("web_search_read", () => {
        expect.step("web_search_read");
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_breadcrumb").toHaveText("Partners Action 1");
    expect(queryAllTexts(".o_kanban_record span")).toEqual(["First record", "Second record"]);
    expect(["web_search_read"]).toVerifySteps();

    try {
        await getService("action").doAction("Boom");
    } catch (e) {
        expect(e.cause).toBeInstanceOf(TypeError);
    }
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_breadcrumb").toHaveText("Partners Action 1");
    expect(queryAllTexts(".o_kanban_record span")).toEqual(["First record", "Second record"]);
    expect(["web_search_read"]).toVerifySteps();
});

test("error in a client action (after the first rendering)", async () => {
    expect.errors(1);

    class Boom extends Component {
        static template = xml`
            <div>
                <t t-if="boom" t-esc="a.b.c"/>
                <button t-else="" class="my_button" t-on-click="onClick">Click Me</button>
            </div>`;
        static props = ["*"];
        setup() {
            this.boom = false;
        }
        get a() {
            // a bit artificial, but makes the test firefox compliant
            throw new Error("Cannot read properties of undefined (reading 'b')");
        }
        onClick() {
            this.boom = true;
            this.render();
        }
    }
    actionRegistry.add("Boom", Boom);

    await mountWithCleanup(WebClient);
    await getService("action").doAction("Boom");
    expect(".my_button").toHaveCount(1);

    await contains(".my_button").click();
    await animationFrame();
    expect(".my_button").toHaveCount(1);
    expect(".o_error_dialog").toHaveCount(1);
    expect(["Cannot read properties of undefined (reading 'b')"]).toVerifyErrors();
});
