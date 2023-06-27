/** @odoo-module **/

import { registry } from "@web/core/registry";
import { shortCutsItem } from "@web/webclient/user_menu/user_menu_items";

export function websiteShortCutsItem(env) {
    const websiteService = env.services["website"];
    return Object.assign({}, shortCutsItem(env), {
        hide: env.isSmall || websiteService.context.snippetsLoaded,
    });
}

registry.category("user_menuitems").add("shortcuts", websiteShortCutsItem, { force: true });
