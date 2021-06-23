/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createWebClient, doAction, getActionManagerServerData } from "./../helpers";

const { Component, tags } = owl;

let serverData;
const actionRegistry = registry.category("actions");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
    });

    QUnit.module("Error handling");

    QUnit.test("error in a client action", async function (assert) {
        assert.expect(4);
        class Boom extends Component {}
        Boom.template = tags.xml`<div><t t-esc="a.b.c"/></div>`;
        actionRegistry.add("Boom", Boom);

        const webClient = await createWebClient({ serverData });
        assert.strictEqual(webClient.el.querySelector(".o_action_manager").innerHTML, "");
        await doAction(webClient, "1");
        const contents = webClient.el.querySelector(".o_action_manager").innerHTML;
        assert.ok(contents !== "");
        try {
            await doAction(webClient, "Boom");
        } catch (e) {
            assert.ok(e instanceof TypeError);
        }
        assert.strictEqual(webClient.el.querySelector(".o_action_manager").innerHTML, contents);
    });
});
