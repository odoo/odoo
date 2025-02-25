import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, mockFetch, runAllTimers } from "@odoo/hoot-mock";
import { Component, onMounted, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    stepAllNetworkCalls,
    webModels,
} from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { FormController } from "@web/views/form/form_controller";
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
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        "form,false": `<form><field name="display_name"/></form>`,
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
        views: [
            [1, "kanban"],
            [false, "form"],
        ],
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
    expect.verifySteps(["web_search_read"]);

    try {
        await getService("action").doAction("Boom");
    } catch (e) {
        expect(e.cause).toBeInstanceOf(TypeError);
    }
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_breadcrumb").toHaveText("Partners Action 1");
    expect(queryAllTexts(".o_kanban_record span")).toEqual(["First record", "Second record"]);
    expect.verifySteps(["web_search_read"]);
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
    expect.verifyErrors(["Cannot read properties of undefined (reading 'b')"]);
});

test("connection lost when opening form view from kanban", async () => {
    expect.errors(2);

    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);

    mockFetch((input) => {
        expect.step(input);
        if (input === "/web/webclient/version_info") {
            // simulate a connection restore at the end of the test, to have no
            // impact on other tests (see connectionLostNotifRemove)
            return true;
        }
        throw new Error(); // simulate a ConnectionLost error
    });
    await contains(".o_kanban_record").click();
    expect(".o_kanban_view").toHaveCount(1);
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification").toHaveText("Connection lost. Trying to reconnect...");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "/web/dataset/call_kw/partner/web_read", // from mockFetch
        "/web/dataset/call_kw/partner/web_search_read", // from mockFetch
    ]);
    await animationFrame();
    expect.verifySteps([]); // doesn't indefinitely try to reload the list

    // cleanup
    await runAllTimers();
    await animationFrame();
    expect.verifySteps(["/web/webclient/version_info"]);
    expect.verifyErrors([Error, Error]);
});

test.tags("desktop");
test("connection lost when coming back to kanban from form", async () => {
    expect.errors(1);

    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);

    await contains(".o_kanban_record").click();
    expect(".o_form_view").toHaveCount(1);

    mockFetch((input) => {
        expect.step(input);
        if (input === "/web/webclient/version_info") {
            // simulate a connection restore at the end of the test, to have no
            // impact on other tests (see connectionLostNotifRemove)
            return true;
        }
        throw new Error(); // simulate a ConnectionLost error
    });
    await contains(".o_breadcrumb .o_back_button a").click();
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification").toHaveText("Connection lost. Trying to reconnect...");
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
        "web_read",
        "/web/dataset/call_kw/partner/web_search_read", // from mockFetch
    ]);
    await animationFrame();
    expect.verifySteps([]); // doesn't indefinitely try to reload the list

    // cleanup
    await runAllTimers();
    await animationFrame();
    expect.verifySteps(["/web/webclient/version_info"]);
    expect.verifyErrors([Error]);
});

test("error on onMounted", async () => {
    expect.errors(1);

    Partner._fields.bar = fields.Boolean();
    Partner._views = {
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        "form,false": `<form><field name="display_name"/><field name="bar"/></form>`,
        "search,false": `<search/>`,
    };
    stepAllNetworkCalls();
    patchWithCleanup(BooleanField.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                throw new Error("faulty on mounted");
            });
        },
    });
    patchWithCleanup(FormController.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                // If a onMounted hook is faulty, the rest of the onMounted will not be executed
                // leading to inconsistent views.
                throw new Error("Never Executed code");
            });
        },
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "web_search_read",
    ]);

    await contains(".o_kanban_record").click();
    await animationFrame();
    expect(".o_form_view").toHaveCount(0);
    // check that the action manager is empty
    expect(".o_action_manager").toHaveText("");
    expect(".o_error_dialog").toHaveCount(1);
    expect.verifySteps(["web_read"]);
    expect.verifyErrors(["Error: faulty on mounted"]);
});
