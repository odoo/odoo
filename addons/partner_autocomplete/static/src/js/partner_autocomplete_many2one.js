odoo.define('partner.autocomplete.many2one', function (require) {
'use strict';

var FieldMany2One = require('web.relational_fields').FieldMany2One;
var core = require('web.core');
var Autocomplete = require('partner.autocomplete.core');
var field_registry = require('web.field_registry');

var _t = core._t;

var PartnerField = FieldMany2One.extend({
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
     * @param search_val {string}
     * @returns {Deferred}
     * @private
     */
    _searchSuggestions: function (search_val) {
        var def = $.Deferred();

        if (Autocomplete.isOnline()) {
            var self = this;

            Autocomplete.autocomplete(search_val).then(function (suggestions) {
                var choices = [];

                if (suggestions && suggestions.length) {
                    choices.push({
                        label: _t('Create and Edit from Autocomplete :'),
                    });
                    _.each(suggestions, function (suggestion) {
                        choices.push({
                            label: _.str.sprintf('%s - %s', suggestion.label, suggestion.description),
                            value: suggestion.domain,
                            action: function () {
                                self._createPartner(suggestion);
                            },
                            classname: 'o_m2o_dropdown_option'
                        });
                    });
                }

                def.resolve(choices)
            });
        } else {
            def.resolve([])
        }

        return def
    },

    /**
     * Action : create popup form with pre-filled values from Autocomplete
     *
     * @param {Object} company
     * @returns {Deferred}
     * @private
     */
    _createPartner: function (company) {
        var self = this;
        self.$('input').val('');

        return Autocomplete.getCreateData(company).then(function(data){
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

field_registry.add('res_partner_many2one', PartnerField);

return PartnerField;
});
