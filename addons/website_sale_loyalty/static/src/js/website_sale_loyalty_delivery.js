/** @odoo-module **/

import PublicWidget from '@web/legacy/js/public/public_widget';
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PublicWidget.registry.websiteSaleDelivery, {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _handleCarrierUpdateResult(carrierInput) {
        await super._handleCarrierUpdateResult(...arguments);
        if (this.result.new_amount_order_discounted) {
            // Update discount of the order
            $('#order_discounted').html(this.result.new_amount_order_discounted);
        }
    },
    /**
     * @override
     */
    _handleCarrierUpdateResultBadge(result) {
        super._handleCarrierUpdateResultBadge(...arguments);
        if (result.new_amount_order_discounted) {
            // We are in freeshipping, so every carrier is Free but we don't
            // want to replace error message by 'Free'
            $('#delivery_carrier .badge:not(.o_wsale_delivery_carrier_error)').text(_t('Free'));
        }
    },
});
