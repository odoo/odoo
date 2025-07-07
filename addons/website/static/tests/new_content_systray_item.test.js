import { expect, test } from "@odoo/hoot";
import { mountWithCleanup, onRpc, contains } from "@web/../tests/web_test_helpers";
import { NewContentSystrayItem } from "@website/client_actions/website_preview/new_content_systray_item";
import { defineWebsiteModels } from "./builder/website_helpers";

defineWebsiteModels();

function setupTest() {
    onRpc("/web/dataset/call_kw/ir.module.module/search_read", () => {
        expect.step("/web/dataset/call_kw/ir.module.module/search_read");
        return [];
    });
    onRpc("/website/check_new_content_access_rights", () => {
        expect.step("/website/check_new_content_access_rights");
        return [];
    });
    onRpc("/website/get_new_page_templates", () => {
        expect.step("/website/get_new_page_templates");
        return [];
    });
}

test("can display a newcontent modal", async () => {
    onRpc(({ route }) => {
        expect.step(route);
        return false;
    });
    setupTest();
    await mountWithCleanup(NewContentSystrayItem, {
        props: {
            onNewPage: () => {},
        },
    });
    await contains(".o_new_content_container button").click();
    expect("div.o_new_content_menu_choices").toHaveCount(1);
    expect.verifySteps([
        "/web/dataset/call_kw/ir.module.module/search_read",
        "/website/check_new_content_access_rights",
        "/website/get_new_page_templates",
    ]);
});
