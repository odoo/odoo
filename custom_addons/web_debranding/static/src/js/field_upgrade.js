/** @odoo-module **/
/*  Copyright 2023 Ivan Yelizariev <https://twitter.com/yelizariev>
    License OPL-1 (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#odoo-apps) for derivative work. */
import { patch } from "@web/core/utils/patch";
import { SearchableSetting } from "@web/webclient/settings_form_view/settings/searchable_setting";

patch(SearchableSetting.prototype, {
    visible() {
        if (!super.visible()) {
            return false;
        }

        // Copy-pasted from addons/web/static/src/webclient/settings_form_view/highlight_text/form_label_highlight_text.js
        const isEnterprise = odoo.info && odoo.info.isEnterprise;
        let upgradeEnterprise = false;
        if (
            this.props.fieldInfo &&
            this.props.fieldInfo.field &&
            this.props.fieldInfo.field.isUpgradeField &&
            !isEnterprise
        ) {
            upgradeEnterprise = true;
        }
        return !upgradeEnterprise;
    },
});
