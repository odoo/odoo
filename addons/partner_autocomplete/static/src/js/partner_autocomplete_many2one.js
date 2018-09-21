odoo.define('partner.autocomplete.many2one', function (require) {
'use strict';

var FieldMany2One = require('web.relational_fields').FieldMany2One;
var core = require('web.core');
var Autocomplete = require('partner.autocomplete.core');
var field_registry = require('web.field_registry');

var _t = core._t;

var PartnerField = FieldMany2One.extend({
    jsLibs: [
        '/partner_autocomplete/static/lib/jsvat.js'
    ],

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._addAutocompleteSource(this._searchSuggestions, {
            placeholder: _t('Searching Autocomplete...'),
            order: 20,
            validation: Autocomplete.validateSearchTerm,
        });

        this.additionalContext['show_vat'] = true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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

        return Autocomplete.getCreateData(company).then(function (data){
            var context = {
                'default_is_company': true
            };
            _.each(data.company, function (val, key) {
                context['default_' + key] = val && val.id ? val.id : val;
            });

            // if(data.company.street_name && !data.company.street_number) context.default_street_number = '';
            if (data.logo) context.default_image = data.logo;

            return self._searchCreatePopup("form", false, context);
        });
    },

    /**
     * Modify autocomplete results rendering
     * Add logo in the autocomplete results if logo is provided
     *
     * @private
     */
    _modifyAutompleteRendering: function (){
        var api = this.$input.data('ui-autocomplete');
        var renderWithoutLogo = api._renderItem;
        api._renderItem = function ( ul, item ) {
            var $li = renderWithoutLogo.call(this, ul, item);
            if (item.logo){
                var $a = $li.find('>a').addClass('o_partner_autocomplete_dropdown_item');
                var $img = $('<img/>').attr('src', item.logo);
                $a.append($img);
            }

            return $li;
        };
    },

    /**
     * @override
     * @private
     */
    _renderEdit: function (){
        this._super.apply(this, arguments);
        this._modifyAutompleteRendering();
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
                        var label =_.str.sprintf('%s - %s', suggestion.label, suggestion.description);
                        label = label.replace(new RegExp(search_val, "gi"), "<b>$&</b>");

                        choices.push({
                            label: label,
                            action: function () {
                                self._createPartner(suggestion);
                            },
                            classname: 'o_m2o_dropdown_option',
                            logo: suggestion.logo,
                        });
                    });
                }

                def.resolve(choices);
            });
        } else {
            def.resolve([]);
        }

        return def;
    },
});

field_registry.add('res_partner_many2one', PartnerField);

return PartnerField;
});
