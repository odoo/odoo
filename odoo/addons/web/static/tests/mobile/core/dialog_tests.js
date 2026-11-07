/** @odoo-module **/

import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { Dialog } from "@web/core/dialog/dialog";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture, mount, dragAndDrop } from "../../helpers/utils";
import { makeFakeDialogService } from "../../helpers/mock_services";

import { Component, xml } from "@odoo/owl";
const serviceRegistry = registry.category("services");
let parent;
let target;

async function makeDialogTestEnv() {
    const env = await makeTestEnv();
    env.dialogData = {
        isActive: true,
        close: () => {},
        scrollToOrigin: () => {},
    };
    return env;
}

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("dialog", makeFakeDialogService());
    });
    hooks.afterEach(() => {
        if (parent) {
            parent = undefined;
        }
    });

    QUnit.module("Dialog");

    QUnit.test("dialog can't be moved on small screen", async (assert) => {
        class Parent extends Component {
            static template = xml`<Dialog>content</Dialog>`;
            static components = { Dialog };
        }

        await mount(Parent, target, { env: await makeDialogTestEnv() });
        const content = target.querySelector(".modal-content");
        assert.strictEqual(content.style.top, "0px");
        assert.strictEqual(content.style.left, "0px");

        const header = content.querySelector(".modal-header");
        const headerRect = header.getBoundingClientRect();
        // Even if the `dragAndDrop` is called, confirms that there are no effects
        await dragAndDrop(header, document.body, {
            // the util function sets the source coordinates at (x; y) + (w/2; h/2)
            // so we need to move the dialog based on these coordinates.
            x: headerRect.x + headerRect.width / 2 + 20,
            y: headerRect.y + headerRect.height / 2 + 50,
        });
        assert.strictEqual(content.style.top, "0px");
        assert.strictEqual(content.style.left, "0px");
    });
});
