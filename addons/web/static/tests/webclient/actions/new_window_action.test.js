import { beforeEach, expect, test } from "@odoo/hoot";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import {
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class TestClientAction extends Component {
    static template = xml`
        <div class="test_client_action">
            ClientAction
        </div>`;
    static props = ["*"];
}

class Partner extends models.Model {
    display_name = fields.Char();

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
        { id: 3, display_name: "Third record" },
        { id: 4, display_name: "Fourth record" },
        { id: 5, display_name: "Fifth record" },
    ];
    _views = {
        form: /* xml */ `
            <form>
                <group>
                    <field name="display_name"/>
                </group>
            </form>`,
        kanban: /* xml */ `
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

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
    },
]);

beforeEach(() => {
    patchWithCleanup(browser, {
        open: (url) => expect.step("open: " + url),
    });
});

test("can execute act_window actions from db ID in a new window", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1, { newWindow: true });
    expect.verifySteps(["open: /odoo/action-1"]);
});

test("'CLEAR-UNCOMMITTED-CHANGES' is not triggered for window action", async () => {
    const webClient = await mountWithCleanup(WebClient);
    webClient.env.bus.addEventListener("CLEAR-UNCOMMITTED-CHANGES", () => {
        expect.step("CLEAR-UNCOMMITTED-CHANGES");
    });

    await getService("action").doAction(1, { newWindow: true });
    expect.verifySteps(["open: /odoo/action-1"]);
});

test("'CLEAR-UNCOMMITTED-CHANGES' is not triggered for client actions", async () => {
    class ClientAction extends Component {
        static template = xml`<div class="o_client_action_test">Hello World</div>`;
        static props = ["*"];
    }
    registry.category("actions").add("my_action", ClientAction);

    const webClient = await mountWithCleanup(WebClient);
    webClient.env.bus.addEventListener("CLEAR-UNCOMMITTED-CHANGES", () => {
        expect.step("CLEAR-UNCOMMITTED-CHANGES");
    });

    await getService("action").doAction("my_action", { newWindow: true });
    expect.verifySteps(["open: /odoo/my_action"]);
});

test("'CLEAR-UNCOMMITTED-CHANGES' is not triggered for switchView", async () => {
    const webClient = await mountWithCleanup(WebClient);
    webClient.env.bus.addEventListener("CLEAR-UNCOMMITTED-CHANGES", () => {
        expect.step("CLEAR-UNCOMMITTED-CHANGES");
    });

    await getService("action").doAction(1);
    await getService("action").switchView("kanban", {}, { newWindow: true });
    expect.verifySteps([
        "CLEAR-UNCOMMITTED-CHANGES", // The first do action clear uncommitted changes as expected. The second one doesn't
        "open: /odoo/action-1",
    ]);
});

test("can execute dynamic act_window actions in a new window", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(
        {
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            res_id: 22,
            views: [[false, "form"]],
        },
        {
            newWindow: true,
        }
    );
    expect.verifySteps(["open: /odoo/m-partner/22"]);
});

test("can execute an actions in a new window and preserve the breadcrumb", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await getService("action").doAction(
        {
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            res_id: 22,
            views: [[false, "form"]],
        },
        {
            newWindow: true,
        }
    );
    expect.verifySteps(["open: /odoo/action-1/m-partner/22"]);
});

test("can execute client actions in a new window", async () => {
    registry.category("actions").add("__test__client__action__", TestClientAction);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(
        {
            name: "Dialog Test",
            target: "current",
            tag: "__test__client__action__",
            type: "ir.actions.client",
        },
        {
            newWindow: true,
        }
    );
    expect.verifySteps(["open: /odoo/__test__client__action__"]);
});
