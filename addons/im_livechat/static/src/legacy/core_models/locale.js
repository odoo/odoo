/** @odoo-module **/

import { attr, Model } from "@im_livechat/legacy/model";

import { localization } from "@web/core/l10n/localization";

Model({
    name: "Locale",
    fields: {
        /**
         * Language used by interface, formatted like {language ISO 2}_{country ISO 2} (eg: fr_FR).
         */
        language: attr({
            compute() {
                return this.env.services.user.lang;
            },
        }),
        textDirection: attr({
            compute() {
                return localization.direction;
            },
        }),
    },
});
