import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "@website/../tests/builder/website_helpers";

defineWebsiteModels();
test("Toggle eCommerce Categories in mega menu", async () => {
    // Minimal mega menu structure: a dropdown-menu.o_mega_menu with nested
    // content containing an element with a class starting with s_mega_menu_.
    const { getEditor } = await setupWebsiteBuilder(`
        <header>
            <div class="dropdown">
                <a class="dropdown-toggle nav-link" href="#" data-bs-toggle="dropdown">Shop</a>
                <div class="dropdown-menu o_mega_menu" data-name="Mega Menu" data-oe-field="mega_menu_content" data-oe-model="website.menu" data-oe-id="1">
                    <div class="some-wrapper">
                        <section class="s_mega_menu_big_icons" data-snippet="s_mega_menu_big_icons"></section>
                    </div>
                </div>
            </div>
        </header>
    `);
    const editor = getEditor();
    const megaMenuEl = editor.document.querySelector(".o_mega_menu");
    expect(megaMenuEl).not.toBe(null);

    // Ensure the mega menu option plugin is available and the builder action
    // can be resolved.
    const toggleAction = editor.shared.builderActions.getAction("toggleFetchEcomCategories");

    // Call the action's load/apply cycle and ensure it does not crash.
    const templateKey = await toggleAction.load({ editingElement: megaMenuEl });
    expect(templateKey.includes("s_mega_menu_")).toBe(true);

    await toggleAction.apply({ editingElement: megaMenuEl, loadResult: templateKey });
});
