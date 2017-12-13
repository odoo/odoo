odoo.define('mail.many2manytags', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_relational = require('web.form_relational');
var Model = require('web.DataModel');
var utils = require('web.utils');

var _t = core._t;

/**
 * Extend of FieldMany2ManyTags widget method.
 * When the user add a partner and the partner don't have an email, open a popup to purpose to add an email.
 * The user can choose to add an email or cancel and close the popup.
 */
var FieldMany2ManyTagsEmail = form_relational.FieldMany2ManyTags.extend({

    start: function() {
        this.mutex = new utils.Mutex();

        // This widget will indirectly trigger a change:value to it's parent widget
        // when setting the value of valid partners. For this reason we have to keep an
        // internal state of the last value in order to compute the effective value changes.
        this.last_processed_value = [];

        this.on("change:value", this, this.on_change_value_check);
        this._super.apply(this, arguments);
    },

    on_change_value_check : function () {
        var self = this;
        var values = this.get('value').slice(0);  // Clone the array

        // We only validate partners emails in case the value is not empty
        // and is different from the last processed value
        var effective_change = _.difference(values, self.last_processed_value).length;
        if (values.length && effective_change) {
            this.mutex.exec(function() {
                return self._check_email_popup(values);
            });
        }
    },

    _check_email_popup: function (ids) {
        var self = this;
        var valid_partners;

        return new Model('res.partner').call("search", [[
                ["id", "in", ids],
                ["email", "=", false],
                ["notify_email", "=", 'always'] ]],
                {context: this.build_context()})
            .then(function (record_ids) {
                var popups_deferreds = [];
                self.valid_partners = _.difference(ids, record_ids);

                // Propose the user to correct invalid partners
                _.each(record_ids, function (id) {
                    var popup_def = $.Deferred();
                    popups_deferreds.push(popup_def);

                    var pop = new form_common.FormViewDialog(self, {
                        res_model: 'res.partner',
                        res_id: id,
                        context: self.build_context(),
                        title: _t("Please complete partner's informations and Email"),
                    }).open();
                    pop.on('write_completed', self, function () {
                        self.valid_partners.push(id);
                    });
                    pop.on('closed', self, function () {
                        popup_def.resolve();
                    });
                });
                return $.when.apply($, popups_deferreds).then(function() {
                    // All popups have been processed for the given ids
                    // It is now time to set the final value with valid partners ids.
                    var filtered_value = _.uniq(self.valid_partners);
                    self.last_processed_value = filtered_value;
                    self.set({'value': filtered_value});
                });
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


/**
 * Registry of form fields
 */
core.form_widget_registry.add('many2many_tags_email', FieldMany2ManyTagsEmail);

});
