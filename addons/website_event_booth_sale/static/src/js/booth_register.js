odoo.define('website_event_booth_sale.booth_registration', function (require) {
'use strict';

const BoothRegistration = require('website_event_booth.booth_registration');

/**
 * This class changes the displayed price after selecting the requested booths.
 */
BoothRegistration.include({

    //--------------------------------------------------------------------------
    // Overrides
    //--------------------------------------------------------------------------

    _onChangeBoothType(ev) {
        this.categoryPrice = parseFloat($(ev.currentTarget).data('price'));
        return this._super.apply(this, arguments);
    },

    /**
     * Updates the displayed total price after selecting the requested booths
     * @param boothCount
     * @private
     */
    _updateUiAfterBoothChange(boothCount) {
        this._super.apply(this, arguments);
        let $elem = this.$('.o_wbooth_booth_total_price');
        $elem.toggleClass('d-none', !boothCount || !this.categoryPrice);
        this._updatePrice(boothCount);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _updatePrice(boothsCount) {
        let $elem = this.$('.o_wbooth_booth_total_price .oe_currency_value');
        $elem.text(boothsCount * this.categoryPrice);
    },

});

});
