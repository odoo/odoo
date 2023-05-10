/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";
import { registerCleanup } from "../../helpers/cleanup";
import { click, getFixture, nextTick, patchWithCleanup } from "../../helpers/utils";
import { errorService } from "@web/core/errors/error_service";

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
        assert.strictEqual(target.querySelector(".breadcrumb").textContent, "Partners Action 1");
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
        assert.containsOnce(target, ".o_kanban_view");
        assert.strictEqual(target.querySelector(".breadcrumb").textContent, "Partners Action 1");
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record span")].map((el) => el.textContent),
            ["yop", "blip", "gnap", "plop", "zoup"]
        );
        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("error in a client action (after the first rendering)", async function (assert) {
        const handler = (ev) => {
            // need to preventDefault to remove error from console (so python test pass)
            ev.preventDefault();
        };
        window.addEventListener("unhandledrejection", handler);
        registerCleanup(() => window.removeEventListener("unhandledrejection", handler));

        patchWithCleanup(QUnit, {
            onUnhandledRejection: () => {},
        });

        registry.category("services").add("error", errorService);

        class Boom extends Component {
            setup() {
                this.boom = false;
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
    });
});
