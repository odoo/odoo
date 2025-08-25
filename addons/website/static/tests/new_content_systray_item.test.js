import { expect, test } from "@odoo/hoot";
import { mountWithCleanup, onRpc} from "@web/../tests/web_test_helpers";
import { NewContentModal } from "@website/client_actions/website_preview/new_content_modal";
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
    await mountWithCleanup(NewContentModal, { props: {
        onNewPage: () => console.log("asdfasdf")
    }});

    expect("div#o_new_content_menu_choices").toHaveCount(1);
    expect.verifySteps([
        "/website/get_new_page_templates",
        "/web/dataset/call_kw/res.users/has_group",
        "/web/dataset/call_kw/ir.module.module/search_read",
        "/website/check_new_content_access_rights",
    ]);
});
