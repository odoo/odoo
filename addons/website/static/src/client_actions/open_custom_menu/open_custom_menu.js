import { registry } from "@web/core/registry";

export async function openCustomMenu(env, action) {
    const websiteCustomMenus = env.services["website_custom_menus"];
    const websiteMenu = websiteCustomMenus.get(action.context.xmlid);
    if (websiteMenu) {
        websiteCustomMenus.open({ xmlid: action.context.xmlid });
    }
}

// TODO we should probably have a more standard system for this
// "website_custom_menus" feature.
registry.category("actions").add("open_website_custom_menu", openCustomMenu);
