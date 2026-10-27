/* @odoo-module */

import { manageMessages } from "@mail/js/tools/debug_manager";

import { registry } from "@web/core/registry";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    createWebClient,
    doAction,
    getActionManagerServerData,
} from "@web/../tests/webclient/helpers";

QUnit.module("debug menu");

QUnit.test("Manage Messages", async (assert) => {
    patchWithCleanup(odoo, { debug: "1" });
    const serverData = getActionManagerServerData();
    // Add fake "mail.message" model and arch
    serverData.models["mail.message"] = {
        fields: { name: { string: "Name", type: "char" } },
        records: [],
    };
    Object.assign(serverData.views, {
        "mail.message,false,list": "<tree/>",
        "mail.message,false,form": "<form/>",
        "mail.message,false,search": "<search/>",
    });
    registry.category("debug").category("form").add("manageMessages", manageMessages);
    async function mockRPC(route, { method, model, kwargs }) {
        if (method === "check_access_rights") {
            return true;
        }
        if (method === "web_search_read" && model === "mail.message") {
            assert.step("message_read");
            const { context, domain } = kwargs;
            assert.strictEqual(context.default_res_id, 5);
            assert.strictEqual(context.default_res_model, "partner");
            assert.deepEqual(domain, ["&", ["res_id", "=", 5], ["model", "=", "partner"]]);
        }
    }
    const target = getFixture();
    const wc = await createWebClient({ serverData, mockRPC });
    await doAction(wc, 3, { viewType: "form", props: { resId: 5 } });
    await click(target, ".o_debug_manager .dropdown-toggle");
    const dropdownItems = target.querySelectorAll(".o_debug_manager .dropdown-menu .dropdown-item");
    assert.strictEqual(dropdownItems.length, 1);
    assert.strictEqual(dropdownItems[0].innerText.trim(), "Manage Messages");

    await click(dropdownItems[0]);
    assert.verifySteps(["message_read"]);
    assert.strictEqual(
        target.querySelector(".o_breadcrumb .active > span").innerText.trim(),
        "Manage Messages"
    );
});
