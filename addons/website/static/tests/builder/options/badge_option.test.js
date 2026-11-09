import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("adjacent s_badge elements should not be merged", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<p><span class="s_badge badge rounded-pill text-bg-primary">Badge 1</span><span class="s_badge badge rounded-pill text-bg-primary">Badge 2</span></p>`
    );
    const editor = getEditor();
    // Trigger mergeAdjacentInlines
    editor.shared.history.addStep();
    expect(editor.editable.querySelectorAll(".s_badge")).toHaveLength(2);
});

test("adjacent s_cta_badge elements should not be merged", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<p><span class="s_cta_badge d-inline-block border rounded">Badge 1</span><span class="s_cta_badge d-inline-block border rounded">Badge 2</span></p>`
    );
    const editor = getEditor();
    editor.shared.history.addStep();
    expect(editor.editable.querySelectorAll(".s_cta_badge")).toHaveLength(2);
});
