odoo.define('base.res_partner_vat_many2one_backend', function (require) {
    "use strict";

    // The goal of this file is to define a custom widget specific for partners
    // many2one to add a new create button when a VAT number is entered, by
    // fetching default data from VIES, if no company with matching data is found
    // in the current database.

    var PartnerFieldMany2One = require('web.res_partner_many2one').PartnerFieldMany2One;
    var concurrency = require('web.concurrency');
    var core = require('web.core');

    var _t = core._t;

    var PartnerVatFieldMany2One = PartnerFieldMany2One.include({
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this._viesDropPrevious = new concurrency.DropPrevious();
            this._addAutocompleteSource(this._searchViesExtraChoices, 'Searching VIES-VAT...', 10, this._validateViesSearchTerm);
        },

        /**
         * Sanitize search value by removing all not alphanumeric
         *
         * @param search_value
         * @returns {string}
         * @private
         */
        _sanitizeVAT: function(search_value){
          return search_value ? search_value.replace(/[^A-Za-z0-9]/g, '') : '';
        },

        /**
         * Check if searched value is possibly a VAT : 2 first chars = alpha + min 5 numbers
         *
         * @param search_val
         * @returns {boolean}
         * @private
         */
        _validateViesSearchTerm: function(search_val) {
            // https://github.com/MfgLabs/js-vat to validate
            var str = this._sanitizeVAT(search_val);
            var regex = /^[A-Za-z]{2}\d{5,}$/g;

            return str && regex.test(str);
        },

        /**
         * Search VIES-VAT API to validate VAT number.
         * If VAT number, return autocomplete result to Create and Edit with data from VIES
         *
         * @param search_val
         * @returns {Promise<Array>}
         * @private
         */
        _searchViesExtraChoices: function (search_val) {
            if (navigator && navigator.onLine) {
                var self = this;

                return self._searchViesVat(search_val).then(function (company_data) {
                    var choices = [];

                    if (company_data) {
                        choices.push({
                            label: _t('Create and Edit from VIES-VAT :'),
                        });

                        choices.push({
                            label: company_data.name + ' - ' + company_data.vat,
                            value: company_data.vat,
                            action: function () {
                                self._createPartnerFromVies.call(self, company_data);
                            },
                            classname: 'o_m2o_dropdown_option'
                        });
                    }

                    return choices;
                });
            } else {
                return false;
            }
        },

        /**
         * Remote call to request VIES-VAT API
         *
         * @param search_val
         * @returns {*|Promise}
         * @private
         */
        _searchViesVat: function (search_val) {
            var def = this._rpc({
                model: this.field.relation,
                method: "vies_vat_search",
                kwargs: {
                    context: this.record.getContext(this.recordParams),
                    search_val: search_val,
                }
            });
            this._viesDropPrevious.add(def);
            return def;
        },

        /**
         * Create a popup form with auto-filled values from VIES
         *
         * @param data
         * @returns {*}
         * @private
         */
        _createPartnerFromVies: function (data) {
            var self = this;
            self.$('input').val('');

            var context = {
                'default_is_company': true
            };
            _.each(data, function (val, key) {
                context['default_' + key] = val && val.id ? val.id : val;
            });

            return self._searchCreatePopup("form", false, context);
        },

    });

    return PartnerVatFieldMany2One;
});