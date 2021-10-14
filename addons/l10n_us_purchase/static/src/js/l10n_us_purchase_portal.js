/** @odoo-module */
import publicWidget from 'web.public.widget';

publicWidget.registry.portalAddress.include({
    /**
     * @override
     * @private
     */
    _adaptAddressForm: function (countryID) {
        this._super.apply(this, arguments);
        var usCountryId = this.$('[data-us_country_id]').data('us_country_id');
        $('input[name="aba_routing"]').parent().toggle(usCountryId == countryID);
    },
});
