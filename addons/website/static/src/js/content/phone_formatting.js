/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.PhoneFormattingInput = publicWidget.Widget.extend({
    selector: 'input[type="tel"]',
    disabledInEditableMode: false,
    /**
     * @override
     */
    start: function () {
        this.$el.on("blur", this._onTelInputBlur.bind(this));

        return this._super(...arguments);
    },
    /**
     * handle formatting of phone number on blur the first time
     * @param ev
     * @returns {Promise<void>}
     * @private
     */
    _onTelInputBlur: async function (ev) {
        const telInput = ev.currentTarget;
        const countrySelect = telInput.closest("form")?.querySelector('select[name="country_id"]');
        if (telInput.value && !telInput.classList.contains("phone_format")) {
            telInput.value = await rpc("/website/format_phone_number", {
                phone_number: telInput.value,
                country_code: session.geoip_country_code,
                country_phone_code: session.geoip_phone_code,
                country_select_id: countrySelect ? countrySelect.value : null,
            });
            telInput.classList.add("phone_format");
        }
    },
    /**
     * @override
     */
    destroy: function () {
        this.$el.off("blur");
        this._super(...arguments);
    },
});
