/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import { click, getFixture, nextTick } from "../../helpers/utils";
import { errorService } from "@web/core/errors/error_service";
import { ConnectionLostError } from "@web/core/network/rpc_service";

import { Component, xml } from "@odoo/owl";

let serverData;
let target;
const actionRegistry = registry.category("actions");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Error handling");

    QUnit.test("error in a client action (at rendering)", async function (assert) {
        assert.expect(11);
        class Boom extends Component {}
        Boom.template = xml`<div><t t-esc="a.b.c"/></div>`;
        actionRegistry.add("Boom", Boom);
        const mockRPC = (route, args) => {
            if (args.method === "web_search_read") {
                assert.step("web_search_read");
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, "1");
        assert.containsOnce(target, ".o_kanban_view");
        assert.strictEqual(target.querySelector(".o_breadcrumb").textContent, "Partners Action 1");
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record span")].map((el) => el.textContent),
            ["yop", "blip", "gnap", "plop", "zoup"]
        );
        assert.verifySteps(["web_search_read"]);

        try {
            await doAction(webClient, "Boom");
        } catch (e) {
            assert.ok(e.cause instanceof TypeError);
        }
        await nextTick();
        assert.containsOnce(target, ".o_kanban_view");
        assert.strictEqual(target.querySelector(".o_breadcrumb").textContent, "Partners Action 1");
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record span")].map((el) => el.textContent),
            ["yop", "blip", "gnap", "plop", "zoup"]
        );
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("error in a client action (after the first rendering)", async function (assert) {
        assert.expectErrors();
        registry.category("services").add("error", errorService);

        class Boom extends Component {
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
        Boom.template = xml`
            <div>
                <t t-if="boom" t-esc="a.b.c"/>
                <button t-else="" class="my_button" t-on-click="onClick">Click Me</button>
            </div>`;
        actionRegistry.add("Boom", Boom);

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, "Boom");
        assert.containsOnce(target, ".my_button");

        await click(document.querySelector(".my_button"));
        await nextTick();
        assert.containsOnce(target, ".my_button");
        assert.containsOnce(target, ".o_error_dialog");
        assert.verifyErrors(["Cannot read properties of undefined (reading 'b')"]);
    });

    QUnit.test("connection lost when opening form view from kanban", async function (assert) {
        assert.expectErrors();
        registry.category("services").add("error", errorService);

        let offline = false;
        const mockRPC = (route, { method }) => {
            assert.step(method || route);
            if (offline) {
                throw new ConnectionLostError(route);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");

        offline = true;
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".o_notification");
        assert.strictEqual(
            target.querySelector(".o_notification").innerText,
            "Connection lost. Trying to reconnect..."
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "web_read",
            "web_search_read",
        ]);
        await nextTick();
        assert.verifySteps([]); // doesn't indefinitely try to reload the list
    });
});
