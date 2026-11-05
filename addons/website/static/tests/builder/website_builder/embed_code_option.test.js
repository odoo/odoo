import { getDragHelper, getInnerContent, waitForEndOfOperation } from "@html_builder/../tests/helpers";
import { expect, test } from "@odoo/hoot";
import { contains, getService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addDropZoneSelector,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("dropping an Embed Code snippet restores its comments", async () => {
    addDropZoneSelector({ selector: "*", dropNear: "section" });
    await setupWebsiteBuilder(`<section><p>Hello</p></section>`, {
        snippets: {
            snippet_content: [
                getInnerContent({
                    name: "Embed Code",
                    content: `
                        <section class="s_embed_code" data-snippet="s_embed_code" data-name="Embed Code">
                            <template class="s_embed_code_saved"><o-comment data-comment="saved"></o-comment><div>x</div></template>
                            <div class="s_embed_code_embedded container o_not_editable"><div>x</div></div>
                        </section>`,
                }),
            ],
        },
    });
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_content .o_snippet_thumbnail"
    ).drag();
    await moveTo(":iframe .oe_drop_zone");
    await drop(getDragHelper());
    await waitForEndOfOperation();

    let codeInEditor;
    patchWithCleanup(getService("dialog"), {
        add(_, { value }, { onClose }) {
            codeInEditor = value;
            onClose();
        },
    });
    await contains(":iframe .s_embed_code").click();
    await contains("[data-action-id='editCode']").click();
    expect(codeInEditor).toBe("<!--saved--><div>x</div>");
});
