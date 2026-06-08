import { animationFrame, expect, test, waitFor } from "@odoo/hoot";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { EditWebsiteSystrayItem } from "@website/client_actions/website_preview/edit_website_systray_item";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

test("Clicking on 'Edit' hides the notification", async () => {
    // simulate delay translation
    onRpc(
        "/test-path",
        () => "<html><body><div id='wrap'><div class='o_delay_translation'>Some text</div></html>"
    );
    patchWithCleanup(EditWebsiteSystrayItem.prototype, {
        get translatable() {
            return true;
        },
        getLocation() {
            return {
                pathname: "/test-path",
                search: "",
                hash: "",
            };
        },
    });
    await setupWebsiteBuilder(
        `<div id="test-element" class="o_delay_translation">Test Element</div>`,
        {
            openEditor: false,
            translateMode: true,
        }
    );
    expect(".o_notification_bar").toHaveCount(0);
    // dispatch content-updated event so we will get the notification
    registry.category("website_systray").dispatchEvent(new CustomEvent("CONTENT-UPDATED"));
    await waitFor(".o_notification_bar");
    // clicking on edit dropdown should hide the notification
    await contains(".o-website-btn-custo-primary:contains('Edit')").click();
    await animationFrame();
    expect(".o_notification_bar").toHaveCount(0);
});
