import { getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { getService, makeTestApp } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { buildEditableInteractions } from "@website/core/website_edit_service";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { Website } from "./mock_server/mock_models/website";
import { WebsitePage } from "./mock_server/mock_models/website_page";
import { WebsiteTrack, WebsiteVisitor } from "./mock_server/mock_models/website_visitor";

export async function switchToEditMode(core) {
    core.stopInteractions();
    const activeInteractions = setupInteractionWhiteList.getWhiteList();
    const unmatchedInteractions = activeInteractions ? new Set(activeInteractions) : new Set();
    const builders = registry.category("public.interactions.edit").getEntries();
    for (const [key, builder] of builders) {
        if (activeInteractions && !activeInteractions.includes(key)) {
            builder.isAbstract = true;
        }
        unmatchedInteractions.delete(key);
    }
    if (unmatchedInteractions.size) {
        throw new Error(`White-listed Interaction does not exist: ${[...unmatchedInteractions]}.`);
    }
    const Interactions = builders.map((builder) => builder[1]);
    const editableInteractions = buildEditableInteractions(Interactions);
    core.activate(editableInteractions);
    await animationFrame();
}

/**
 * Sets up the website services with an empty page document and returns a
 * function giving the xmlids of the menus displayed by `website_custom_menus`
 * among `menuXmlids`, for a page whose `<html>` dataset is `dataset`.
 *
 * @param {string[]} menuXmlids
 * @returns {Promise<(dataset: Object) => string[]>}
 */
export async function setupWebsiteCustomMenus(menuXmlids) {
    await makeTestApp();
    const website = getService("website");
    const websiteCustomMenus = getService("website_custom_menus");
    await website.fetchUserGroups();
    await website.fetchWebsites();
    website.currentWebsiteId = 1;
    const iframeEl = document.createElement("iframe");
    iframeEl.hidden = true;
    getFixture().appendChild(iframeEl);
    const pageDocument = iframeEl.contentDocument;
    pageDocument.documentElement.lang = "en-US";
    const sections = menuXmlids.map((xmlid) => ({ xmlid, children: [], childrenTree: [] }));
    return (dataset) => {
        const htmlDataset = pageDocument.documentElement.dataset;
        for (const key of Object.keys(htmlDataset)) {
            delete htmlDataset[key];
        }
        Object.assign(htmlDataset, dataset);
        website.pageDocument = pageDocument;
        return websiteCustomMenus.addCustomMenus(sections).map((menu) => menu.xmlid);
    };
}

export const websiteModels = {
    Website,
    WebsitePage,
    WebsiteTrack,
    WebsiteVisitor,
};
