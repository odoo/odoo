openerp_FieldMany2ManyTagsEmail = function(instance) {
var _t = instance.web._t;

/**
 * Extend of FieldMany2ManyTags widget method.
 * When the user add a partner and the partner don't have an email, open a popup to purpose to add an email.
 * The user can choose to add an email or cancel and close the popup.
 */
instance.web.form.FieldMany2ManyTagsEmail = instance.web.form.FieldMany2ManyTags.extend({

    start: function() {
        this.mutex = new openerp.Mutex();

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

        new instance.web.Model('res.partner').call("search", [[
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

                    var pop = new instance.web.form.FormOpenPopup(self);
                    pop.show_element(
                        'res.partner',
                        id,
                        self.build_context(),
                        {
                            title: _t("Please complete partner's informations and Email"),
                        }
                    );
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
});


/**
 * Registry of form fields
 */
instance.web.form.widgets = instance.web.form.widgets.extend({
    'many2many_tags_email' : 'instance.web.form.FieldMany2ManyTagsEmail',
});

};
