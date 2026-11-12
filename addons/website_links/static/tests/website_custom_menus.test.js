import { expect, getFixture, test } from "@odoo/hoot";
import { getService, makeTestApp } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels } from "@website/../tests/builder/website_helpers";
import "@website_links/services/website_custom_menus";

defineWebsiteModels();

test("hide page actions on error pages and restore them on normal pages", async () => {
    await makeTestApp();
    const website = getService("website");
    const websiteCustomMenus = getService("website_custom_menus");
    await website.fetchUserGroups();
    await website.fetchWebsites();
    const iframeEl = document.createElement("iframe");
    iframeEl.hidden = true;
    getFixture().appendChild(iframeEl);
    const pageDocument = iframeEl.contentDocument;
    pageDocument.documentElement.lang = "en-US";
    Object.assign(pageDocument.documentElement.dataset, {
        websiteId: "1",
        mainObject: "ir.ui.view(1,)",
        canOptimizeSeo: "True",
    });
    website.currentWebsiteId = 1;
    const menuXmlids = [
        "website.menu_page_properties",
        "website.menu_optimize_seo",
        "website_links.menu_link_tracker",
        "website.menu_ace_editor",
    ];
    const sections = menuXmlids.map((xmlid) => ({ xmlid, children: [], childrenTree: [] }));

    for (const isErrorPage of [false, true, false]) {
        pageDocument.documentElement.dataset.isErrorPage = isErrorPage ? "True" : "False";
        pageDocument.documentElement.dataset.viewXmlid = isErrorPage
            ? "website.page_404"
            : "website.contactus";
        website.pageDocument = pageDocument;
        const visibleMenus = websiteCustomMenus.addCustomMenus(sections);
        expect(visibleMenus.map((menu) => menu.xmlid)).toEqual(
            isErrorPage ? ["website.menu_ace_editor"] : menuXmlids
        );
    }

    delete pageDocument.documentElement.dataset.websiteId;
    website.pageDocument = pageDocument;
    expect(websiteCustomMenus.addCustomMenus(sections)).toEqual([]);
});
