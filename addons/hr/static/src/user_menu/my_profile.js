/** @odoo-module **/

import { registry } from "@web/core/registry";
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items";

export function hrPreferencesItem(env)  {
    return Object.assign(
        {}, 
        preferencesItem(env),
        {
            description: env._t('My Profile'),
        }
    );
}

registry.category("user_menuitems").add('profile', hrPreferencesItem, { force: true })
