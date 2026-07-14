import { Component } from '@odoo/owl';
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsiteSale.include({
    /**
     * Trigger a state update of the ClickAndCollectAvailability component when the combination info
     * is updated.
     *
     * @override
     */
    _onChangeCombination(ev, $parent, combination) {
        const res = this._super.apply(this, arguments);
        Component.env.bus.trigger('updateCombinationInfo', combination);
        return res;
    },

});
