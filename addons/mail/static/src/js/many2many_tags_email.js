odoo.define('mail.many2manytags', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var core = require('web.core');
var form_common = require('web.view_dialogs');
var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');

var M2MTags = relational_fields.FieldMany2ManyTags;
var _t = core._t;

BasicModel.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} record - an element from the localData
     * @param {string} fieldName
     * @return {Deferred<Object>} the deferred is resolved with the
     *                            invalidPartnerIds
     */
    _setInvalidMany2ManyTagsEmail: function (record, fieldName) {
        var self = this;
        var localID = (record._changes && fieldName in record._changes) ?
                        record._changes[fieldName] :
                        record.data[fieldName];
        var list = this._applyX2ManyOperations(this.localData[localID]);
        var invalidPartnerIds = [];
        _.each(list.data, function (id) {
            var record = self.localData[id];
            if (!record.data.email) {
                invalidPartnerIds.push(record);
            }
        });
        var def;
        if (invalidPartnerIds) {
            // remove invalid partners
            var changes = {operation: 'DELETE', ids: _.pluck(invalidPartnerIds, 'id')};
            def = this._applyX2ManyChange(record, fieldName, changes);
        }
        return $.when(def).then(function () {
            return $.when({
                invalidPartnerIds: _.pluck(invalidPartnerIds, 'res_id'),
            });
        });
    },
});

var FieldMany2ManyTagsEmail = M2MTags.extend({
    fieldsToFetch: _.extend({}, M2MTags.prototype.fieldsToFetch, {
        email: {type: 'char'},
    }),
    specialData: "_setInvalidMany2ManyTagsEmail",

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Open a popup for each invalid partners (without email) to fill the email.
     *
     * @private
     * @returns {Deferred}
     */
    _checkEmailPopup: function () {
        var self = this;

        var popupDefs = [];
        var validPartners = [];

        // propose the user to correct invalid partners
        _.each(this.record.specialData[this.name].invalidPartnerIds, function (resID) {
            var def = $.Deferred();
            popupDefs.push(def);

            var pop = new form_common.FormViewDialog(self, {
                res_model: self.field.relation,
                res_id: resID,
                context: self.record.context,
                title: _t("Please complete customer's informations and email"),
                on_saved: function (record) {
                    if (record.data.email) {
                        validPartners.push(record.res_id);
                    }
                },
            }).open();
            pop.on('closed', self, function () {
                def.resolve();
            });
        });
        return $.when.apply($, popupDefs).then(function() {
            // All popups have been processed for the given ids
            // It is now time to set the final value with valid partners ids.
            validPartners = _.uniq(validPartners);
            if (validPartners.length) {
                var values = _.map(validPartners, function (id) {
                    return {id: id};
                });
                self._setValue({
                    operation: 'ADD_M2M',
                    ids: values,
                });
            }
        });
    },
    /**
     * Override to check if all many2many values have an email set before
     * rendering the widget.
     *
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        var def = $.Deferred();
        var _super = this._super.bind(this);
        if (this.record.specialData[this.name].invalidPartnerIds.length) {
            def = this._checkEmailPopup();
        } else {
            def.resolve();
        }
        return def.then(function () {
            return _super.apply(self, arguments);
        });
    },

    /**
     * Override for res.partner
     * name_get is dynamic (based on context) while display_name is static
     * (stored)
     */
    get_render_data: function(ids){
        this.dataset.cancel_read();
        return this.dataset.name_get(ids).then(function (names) {
            return _.map(names, function(name) {
                return {id: name[0], display_name: name[1]};
            });
        });
    },

});

field_registry.add('many2many_tags_email', FieldMany2ManyTagsEmail);

});
