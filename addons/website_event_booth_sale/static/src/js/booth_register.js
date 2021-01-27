odoo.define('website_event_booth_sale.booth_registration', function (require) {
'use strict';

const BoothRegistration = require('website_event_booth.booth_registration');

BoothRegistration.include({

    _onChangeBoothType(ev) {
        this.categoryPrice = parseFloat($(ev.currentTarget).data('price-reduce'));
        return this._super.apply(this, arguments);
    },

    _updateUiAfterBoothChange(boothCount) {
        this._super.apply(this, arguments);
        let $elem = this.$('.o_wevent_booths_total_price');
        $elem.toggleClass('d-none', !boothCount);
        this._updatePrice(boothCount);
    },

    _updatePrice(boothsCount) {
        let $elem = this.$('.o_wevent_booths_total_price .oe_currency_value');
        $elem.text(boothsCount * this.categoryPrice);
    },

});

});
