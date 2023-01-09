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
        assert.expect(4);
        class Boom extends Component {}
        Boom.template = xml`<div><t t-esc="a.b.c"/></div>`;
        actionRegistry.add("Boom", Boom);

        const webClient = await createWebClient({ serverData });
        assert.strictEqual(target.querySelector(".o_action_manager").innerHTML, "");
        await doAction(webClient, "1");
        const contents = target.querySelector(".o_action_manager").innerHTML;
        assert.ok(contents !== "");
        try {
            await doAction(webClient, "Boom");
        } catch (e) {
            assert.ok(e.cause instanceof TypeError);
        }
        assert.strictEqual(target.querySelector(".o_action_manager").innerHTML, contents);
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
        assert.containsOnce(target, ".o_dialog_error");
    });
});
