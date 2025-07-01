import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items";

export function hrPreferencesItem(env)  {
    return Object.assign(
        {}, 
        preferencesItem(env),
        {
            description: _t('My Preferences'),
        }
    );
}

registry.category("user_menuitems").add('preferences', hrPreferencesItem, { force: true })
