odoo.define('web.res_partner_many2one_clearbit', function (require) {
    'use strict';

    var PartnerFieldMany2One = require('web.res_partner_many2one').PartnerFieldMany2One;
    var core = require('web.core');
    var Clearbit = require('clearbit.core');

    var _t = core._t;

    var PartnerField = PartnerFieldMany2One.include({
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this._addAutocompleteSource(this._searchClearbitExtraChoices, 'Searching Clearbit...', 20, function(term){
                return Clearbit.validateSearchTerm(term)
            });
        },

        /**
         * Query Clearbit and add results to the popup
         *
         * @override
         * @param search_val
         * @returns {*}
         * @private
         */
        _searchClearbitExtraChoices: function (search_val) {
            console.log(true)
            if (Clearbit.isOnline()) {
                var self = this;

                return Clearbit.autocomplete(search_val).then(function (suggestions) {
                    var choices = [];

                    if (suggestions && suggestions.length) {
                        choices.push({
                            label: _t('Create and Edit from Clearbit :'),
                        });
                        _.each(suggestions, function (suggestion) {
                            choices.push({
                                label: suggestion.name + ' (' + suggestion.domain + ')',
                                value: suggestion.domain,
                                action: function () {
                                    self._createPartnerFromClearbit(suggestion.domain);
                                },
                                classname: 'o_m2o_dropdown_option'
                            })
                        });
                    }

                    return choices;
                });
            } else {
                return false;
            }
        },

        /**
         * Action : create popup form with pre-filled values from Clearbit API
         *
         * @param company_domain
         * @returns Promise
         * @private
         */
        _createPartnerFromClearbit: function (company_domain) {
            var self = this;
            self.$('input').val('');

            // Fetch additionnal company info via Clearbit Enrichment API
            var enrichPromise = Clearbit.enrichCompany(company_domain);

            // Get logo
            var logoPromise = Clearbit.getCompanyLogo(company_domain);

            return $.when(enrichPromise, logoPromise).done(function (data, logo) {
                var context = {
                    'default_is_company': true
                };
                _.each(data, function (val, key) {
                    context['default_' + key] = val && val.id ? val.id : val;
                });
                if (logo) context.default_image = logo;

                return self._searchCreatePopup("form", false, context);
            });
        },

    });

    return PartnerField;
});
