/** @odoo-module **/

import { manageMessages } from "@mail/js/tools/debug_manager";
import { click, legacyExtraNextTick } from "@web/../tests/helpers/utils";
import {
    createWebClient,
    doAction,
    getActionManagerTestConfig,
} from "@web/../tests/webclient/actions/helpers";
import { debugService } from "@web/core/debug/debug_service";
import { registry } from "@web/core/registry";

QUnit.module("DebugMenu");

QUnit.test("Manage Messages", async function (assert) {
    assert.expect(6);

    const testConfig = Object.assign(getActionManagerTestConfig(), {
        debug: "1",
    });

    // Add fake "mail.message" model and arch
    testConfig.serverData.models["mail.message"] = {
        fields: { name: { string: "Name", type: "char" } },
        records: [],
    };
    Object.assign(testConfig.serverData.views, {
        "mail.message,false,list": `<tree/>`,
        "mail.message,false,form": `<form/>`,
        "mail.message,false,search": `<search/>`,
    });

    // Activate debug service with "Manage Message" item
    registry.category("services").add("debug", debugService);
    registry.category("debug").category("form").add("manageMessages", manageMessages);

    async function mockRPC(route, args) {
        if (args.method === "check_access_rights") {
            return true;
        }
        if (route === "/web/dataset/search_read" && args.model === "mail.message") {
            assert.strictEqual(args.context.default_res_id, 5);
            assert.strictEqual(args.context.default_res_model, "partner");
            assert.deepEqual(args.domain, ["&", ["res_id", "=", 5], ["model", "=", "partner"]]);
        }
    }

    const wc = await createWebClient({ testConfig, mockRPC });
    await doAction(wc, 3, { viewType: "form", resId: 5 });
    await legacyExtraNextTick();
    await click(wc.el, ".o_debug_manager .o_dropdown_toggler");

    const dropdownItems = wc.el.querySelectorAll(
        ".o_debug_manager .o_dropdown_menu .o_dropdown_item"
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
        wc.el.querySelector(".breadcrumb-item.active").innerText.trim(),
        "Manage Messages"
    );
});
