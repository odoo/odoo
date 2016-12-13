odoo.define('mail.many2manytags', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_relational = require('web.form_relational');
var Model = require('web.DataModel');

var _t = core._t;

/**
 * Extend of FieldMany2ManyTags widget method.
 * When the user add a partner and the partner don't have an email, open a popup to purpose to add an email.
 * The user can choose to add an email or cancel and close the popup.
 */
var FieldMany2ManyTagsEmail = form_relational.FieldMany2ManyTags.extend({

    start: function() {
        this.values = [];
        this.values_checking = [];

        this.on("change:value", this, this.on_change_value_check);
        this.trigger("change:value");

        this._super.apply(this, arguments);
    },

    on_change_value_check : function () {
        this.values = _.uniq(this.values);

        // filter for removed values
        var values_removed = _.difference(this.values, this.get('value'));
        if (values_removed.length) {
            this.values = _.difference(this.values, values_removed);
            this.set({'value': this.values});
            return false;
        }

        // find not checked values that are not currently on checking
        var not_checked = _.difference(this.get('value'), this.values, this.values_checking);
        if (not_checked.length) {
            // remember values on checking for cheked only one time
            this.values_checking = this.values_checking.concat(not_checked);
            // check values
            this._check_email_popup(not_checked);
        }
    },

    _check_email_popup: function (ids) {
        var self = this;
        new Model('res.partner').call("search", [[
                ["id", "in", ids], 
                ["email", "=", false] ]], 
                {context: this.build_context()})
            .then(function (record_ids) {
                // valid partner
                var valid_partner = _.difference(ids, record_ids);
                self.values = self.values.concat(valid_partner);
                self.values_checking = _.difference(self.values_checking, valid_partner);

                // unvalid partner
                _.each(record_ids, function (id) {
                    var pop = new form_common.FormViewDialog(self, {
                        res_model: 'res.partner',
                        res_id: id,
                        context: self.build_context(),
                        title: _t("Please complete partner's informations and Email"),
                    }).open();
                    pop.on('write_completed', self, function () {
                        this.values.push(id);
                        this.values_checking = _.without(this.values_checking, id);
                        this.set({'value': this.values});
                    });
                    pop.on('closed', self, function () {
                        this.values_checking = _.without(this.values_checking, id);
                        this.set({'value': this.values});
                    });
                });
            });
    },
});


/**
 * Registry of form fields
 */
core.form_widget_registry.add('many2many_tags_email', FieldMany2ManyTagsEmail);

});
