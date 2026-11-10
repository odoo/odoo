import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels } from "@website/../tests/builder/website_helpers";
import { setupWebsiteCustomMenus } from "@website/../tests/helpers";
import "@website/services/website_custom_menus";

defineWebsiteModels();

test("hide page actions on error pages and restore them on normal pages", async () => {
    const menuXmlids = [
        "website.menu_page_properties",
        "website.menu_optimize_seo",
        "website.menu_ace_editor",
    ];
    const getDisplayedMenus = await setupWebsiteCustomMenus(menuXmlids);
    const page = {
        websiteId: "1",
        mainObject: "ir.ui.view(1,)",
        canOptimizeSeo: "True",
        viewXmlid: "website.contactus",
    };
    const errorPage = { ...page, isErrorPage: "True", viewXmlid: "website.page_404" };

    expect(getDisplayedMenus(page)).toEqual(menuXmlids);
    expect(getDisplayedMenus(errorPage)).toEqual(["website.menu_ace_editor"]);
    expect(getDisplayedMenus(page)).toEqual(menuXmlids);
});
