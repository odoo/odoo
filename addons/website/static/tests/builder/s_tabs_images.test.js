import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import { defineWebsiteModels, setupWebsiteBuilderWithSnippet } from "./website_helpers";

defineWebsiteModels();

test("pressing Enter in the .s_tabs_images_option doesn't add a new <li/>", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_tabs_images");
    const editor = getEditor();
    const numberOfSlides = queryOne(":iframe .s_tabs_images ul").children.length;
    setSelection({ anchorNode: queryOne(":iframe .s_tabs_images ul>li:last-child small") });
    // Simulate pressing "enter"
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    expect(":iframe .s_tabs_images ul>li").toHaveCount(numberOfSlides);
});
