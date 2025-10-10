import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { getDragHelper, waitForEndOfOperation } from "@html_builder/../tests/helpers";

defineWebsiteModels();

test("Drag and drop an inner snippet having a drag image preview", async () => {
    await setupWebsiteBuilderWithSnippet(["s_text_image"]);
    const dragUtils = await contains(
        "#snippet_content [name='Drag Image Preview Test'] .o_snippet_thumbnail"
    ).drag();
    await dragUtils.moveTo(":iframe .s_text_image .oe_drop_zone");
    expect(":iframe .s_drag_image_preview_test").toHaveClass("o_snippet_previewing_on_drag");
    expect(":iframe .s_drag_image_preview_test > div.o_snippet_drag_preview").toHaveCount(1);
    await dragUtils.drop(getDragHelper());
    await waitForEndOfOperation();
    expect(":iframe .s_drag_image_preview_test").not.toHaveClass("o_snippet_previewing_on_drag");
    expect(":iframe .s_drag_image_preview_test > div.o_snippet_drag_preview").toHaveCount(0);
});
