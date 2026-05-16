import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("Save several megamenu", async () => {
    const savedMenus = new Set();

    onRpc("ir.ui.view", "save", ({ args }) => true);
    onRpc("website.menu", "write", ({ args: [[id], value] }) => {
        expect(value).toEqual({ mega_menu_classes: "o_mega_menu_container_size" });
        savedMenus.add(id);
        expect.step(`save mega menu`);
        return true;
    });

    await setupWebsiteBuilder("", {
        headerContent: `
            <div data-name="Mega Menu" data-oe-xpath="/t[1]/li[2]/div[1]" class="o_mega_menu" data-oe-model="website.menu" data-oe-id="1" data-oe-field="mega_menu_content" data-oe-type="html" data-oe-expression="submenu.mega_menu_content">
                <section class="s_mega_menu_odoo_menu pt16 o_cc o_cc1">
                    <div class="container">
                        mega menu 1 content
                    </div>
                </section>
            </div>
            <div data-name="Mega Menu" data-oe-xpath="/t[1]/li[2]/div[1]" class="o_mega_menu" data-oe-model="website.menu" data-oe-id="2" data-oe-field="mega_menu_content" data-oe-type="html" data-oe-expression="submenu.mega_menu_content">
                <section class="s_mega_menu_odoo_menu pt16 o_cc o_cc1">
                    <div class="container">
                        mega menu 2 content
                    </div>
                </section>
            </div>
        `,
    });
    await contains(":iframe [data-oe-id='1']").click();
    await contains("[data-label=Size] button.dropdown").click();
    await contains(".dropdown-item:contains(Narrow)").click();

    await contains(":iframe [data-oe-id='2']").click();
    await contains("[data-label=Size] button.dropdown").click();
    await contains(".dropdown-item:contains(Narrow)").click();

    await contains("[data-action=save]").click();

    await expect.waitForSteps(["save mega menu", "save mega menu"]);
    expect(savedMenus).toEqual(new Set([1, 2]), { message: "both menu have been saved" });
});
