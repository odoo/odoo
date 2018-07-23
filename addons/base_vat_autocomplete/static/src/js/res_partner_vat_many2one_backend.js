odoo.define('base.res_partner_vat_many2one_backend', function (require) {
// The goal of this file is to define a custom widget specific for partners
// many2one to add a new create button when a VAT number is entered, by
// fetching default data from VIES, if no company with matching data is found
// in the current database.

"use strict";
var fieldRegistry = require('web.field_registry');
var FieldMany2One = require('web.relational_fields').FieldMany2One;
var core = require('web.core');

var _t = core._t;

var PartnerVatFieldMany2One = FieldMany2One.extend({
    /**
     * @private
     * @override
     */
    _search: function (search_val, additionalContext) {
        var self = this;
        var def = $.Deferred();

        var context = _.extend(additionalContext, { 'query_vies': true});

        var parent = this._super.apply(this, search_val, context);

        // TODO also intercept the M2ODialog to give it the proper context

        // TODO maybe code this better

        parent.then(function (values) {
            self._searchVat(search_val).then(function (result) {
                if (result[0] && result[1]) {

                    var context = {
                        default_city: result[1].city,
                        default_country_id: result[1].country_id,
                        default_is_company: true,
                        default_name: result[0],
                        default_street: result[1].street,
                        default_vat: search_val,
                        default_zip: result[1].zip,
                    };

                    var companySpan = $('<span />').text(result[0]).html();

                    var create_enabled = self.can_create && !self.nodeOptions.no_create;
                    var raw_result = _.map(result, function (x) { return x[1]; });

                    if (create_enabled && !self.nodeOptions.no_quick_create &&
                        search_val.length > 0 && !_.contains(raw_result, search_val)
                    ) {
                        values.splice(-2, 1, {
                            label: _.str.sprintf(_t('Create "<strong>%s</strong>"'), companySpan),
                            action: self._quickCreate.bind(self, search_val),
                            classname: 'o_m2o_dropdown_option'
                        });
                    }
                    if (create_enabled && !self.nodeOptions.no_create_edit) {
                        var createAndEditAction = function () {
                            
                            return self._searchCreatePopup("form", false, context);
                        };
                        values.splice(-1, 1, {
                            label: _.str.sprintf(_t('Create and Edit "<strong>%s</strong>"'), companySpan),
                            action: createAndEditAction,
                            classname: 'o_m2o_dropdown_option',
                        });
                    }
                }
                def.resolve(values);
            });
        });

        return def;
    },

    _searchVat: function (search_val) {
        var def = $.Deferred();
        var context = this.record.getContext(this.recordParams);

        this._rpc({
            model: this.field.relation,
            method: "vat_search",
            kwargs: {
                context: context,
                search_val: search_val,
            }
        }).then(function (result) {
            def.resolve(result);
        });

        return def;
    }

});

fieldRegistry.add('res_partner_vat_many2one', PartnerVatFieldMany2One);
});