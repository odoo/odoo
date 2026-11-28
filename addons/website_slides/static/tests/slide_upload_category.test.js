import { animationFrame, expect, runAllTimers, test } from "@odoo/hoot";
import { click, edit } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { SlideUploadCategory } from "@website_slides/js/public/components/slide_upload_dialog/slide_upload_category";
import { defineWebsiteSlidesModels } from "@website_slides/../tests/website_slides_test_helpers";

defineWebsiteSlidesModels();

class Parent extends Component {
    static components = { SlideUploadCategory };
    static props = ["*"];
    static template = xml`
        <div id="o_w_slide_upload_btns"/>
        <SlideUploadCategory
            channelId="1"
            slideCategory="'article'"
            canPublish="true"
            canUpload="true"
            upload="() => {}"
        >
            <t t-set-slot="tutorial"/>
        </SlideUploadCategory>
    `;
}

onRpc("/slides/category/search_read", () => ({ read_results: [] }));
onRpc("/slides/tag/search_read", () => ({ read_results: [{ id: 1, name: "Practice" }] }));

async function typeInTags(value) {
    await mountWithCleanup(Parent);
    await click("[data-label='Tags'] .o_select_menu_toggler");
    await animationFrame();
    await edit(value);
    await runAllTimers();
    await animationFrame();
}

test("typing a new tag name proposes to create it", async () => {
    await typeInTags("Newtag");
    expect(".o-dropdown-item:contains('Create New Tag')").toHaveCount(1);
});

test("a tag created from the upload dialog is selected", async () => {
    await typeInTags("Newtag");
    await click(".o-dropdown-item:contains('Create New Tag')");
    await animationFrame();
    expect("[data-label='Tags'] .o_tag_badge_text").toHaveText("Newtag");
});
