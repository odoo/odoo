/** @odoo-module **/

import { manageMessages } from "@mail/js/tools/debug_manager";
import { click, getFixture, legacyExtraNextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";

QUnit.module("DebugMenu");

QUnit.test("Manage Messages", async function (assert) {
    assert.expect(6);

    patchWithCleanup(odoo, { debug: "1" });
    const serverData = getActionManagerServerData();

    // Add fake "mail.message" model and arch
    serverData.models["mail.message"] = {
        fields: { name: { string: "Name", type: "char" } },
        records: [],
    };
    Object.assign(serverData.views, {
        "mail.message,false,list": `<tree/>`,
        "mail.message,false,form": `<form/>`,
        "mail.message,false,search": `<search/>`,
    });

    registry.category("debug").category("form").add("manageMessages", manageMessages);

    async function mockRPC(route, { method, model, kwargs }) {
        if (method === "check_access_rights") {
            return true;
        }
        if (method === "web_search_read" && model === "mail.message") {
            const { context, domain } = kwargs;
            assert.strictEqual(context.default_res_id, 5);
            assert.strictEqual(context.default_res_model, "partner");
            assert.deepEqual(domain, ["&", ["res_id", "=", 5], ["model", "=", "partner"]]);
        }
    }

    const target = getFixture();
    const wc = await createWebClient({ serverData, mockRPC });
    await doAction(wc, 3, { viewType: "form", props: { resId: 5 } });
    await legacyExtraNextTick();
    await click(target, ".o_debug_manager .dropdown-toggle");

    const dropdownItems = target.querySelectorAll(
        ".o_debug_manager .dropdown-menu .dropdown-item"
    );
    assert.strictEqual(dropdownItems.length, 1);
    assert.strictEqual(
        dropdownItems[0].innerText.trim(),
        "Manage Messages",
        "should have correct menu item text"
    );

    await click(dropdownItems[0]);
    await legacyExtraNextTick();

    assert.strictEqual(
        target.querySelector(".breadcrumb-item.active").innerText.trim(),
        "Manage Messages"
    );
});
