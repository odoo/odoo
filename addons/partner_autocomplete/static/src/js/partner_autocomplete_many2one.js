odoo.define('partner.autocomplete.many2one', function (require) {
    'use strict';

    var PartnerFieldMany2One = require('web.res_partner_many2one').PartnerFieldMany2One;
    var core = require('web.core');
    var Autocomplete = require('partner.autocomplete.core');

    var _t = core._t;

    var PartnerField = PartnerFieldMany2One.include({
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this._addAutocompleteSource(this._searchSuggestions, 'Searching Autocomplete...', 20, function(term){
                return Autocomplete.validateSearchTerm(term)
            });
        },

        /**
         * Query Autocomplete and add results to the popup
         *
         * @override
         * @param search_val
         * @returns {*}
         * @private
         */
        _searchSuggestions: function (search_val) {
            if (Autocomplete.isOnline()) {
                var self = this;

                return Autocomplete.autocomplete(search_val).then(function (suggestions) {
                    var choices = [];

                    if (suggestions && suggestions.length) {
                        choices.push({
                            label: _t('Create and Edit from Autocomplete :'),
                        });
                        _.each(suggestions, function (suggestion) {
                            choices.push({
                                label: _.str.sprintf('%s (%s)', suggestion.label, suggestion.description),
                                value: suggestion.domain,
                                action: function () {
                                    self._createPartner(suggestion);
                                },
                                classname: 'o_m2o_dropdown_option'
                            });
                        });
                    }

                    return choices;
                });
            } else {
                return false;
            }
        },

        /**
         * Action : create popup form with pre-filled values from Autocomplete
         *
         * @param company
         * @returns Promise
         * @private
         */
        _createPartner: function (company) {
            var self = this;
            self.$('input').val('');

            Autocomplete.getCreateData(company).then(function(data){
                var context = {
                    'default_is_company': true
                };
                _.each(data.company, function (val, key) {
                    context['default_' + key] = val && val.id ? val.id : val;
                });
                if (data.logo) context.default_image = data.logo;

                return self._searchCreatePopup("form", false, context);
            });
        },

    });

    return PartnerField;
});
