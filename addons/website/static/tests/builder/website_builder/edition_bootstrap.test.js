import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Opening a dropdown should not add mutations to the history", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<a href="#" role="button" data-bs-toggle="dropdown" class="dropdown-toggle">Toggle</a>
        <div role="menu" class="dropdown-menu">
            <a href="#" role="menuitem" class="dropdown-item">Item</a>
        </div>`,
        {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        }
    );
    await contains(":iframe .dropdown-toggle").click();
    const editor = getEditor();
    expect(":iframe .dropdown-toggle").toHaveClass("show");
    expect(editor.shared.history.addStep()).toBe(false);
});

test("Opening an offcancas should not add mutations to the history", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `
<button class="toggleCanvas" type="button" data-bs-toggle="offcanvas" data-bs-target="#offcanvasExample">
  Button
</button>

<div class="offcanvas offcanvas-start" id="offcanvasExample" >
  <div class="offcanvas-header">Header</div>
  <div class="offcanvas-body">Body</div>
</div>`,
        {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        }
    );
    await contains(":iframe .toggleCanvas").click();
    const editor = getEditor();
    await waitFor(":iframe .offcanvas.show");
    expect(editor.shared.history.addStep()).toBe(false);
});
