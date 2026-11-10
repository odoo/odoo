import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels } from "@website/../tests/builder/website_helpers";
import { setupWebsiteCustomMenus } from "@website/../tests/helpers";
import "@website_links/services/website_custom_menus";

defineWebsiteModels();

test("hide link tracker on error pages and on pages without page data", async () => {
    const getDisplayedMenus = await setupWebsiteCustomMenus(["website_links.menu_link_tracker"]);
    const page = { websiteId: "1", mainObject: "ir.ui.view(1,)" };

    expect(getDisplayedMenus(page)).toEqual(["website_links.menu_link_tracker"]);
    expect(getDisplayedMenus({ ...page, isErrorPage: "True" })).toEqual([]);
    expect(getDisplayedMenus({})).toEqual([]);
});
