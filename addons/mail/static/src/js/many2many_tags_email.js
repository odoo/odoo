openerp_FieldMany2ManyTagsEmail = function(instance) {
var _t = instance.web._t;

/**
 * Extend of FieldMany2ManyTags widget method.
 * When the user add a partner and the partner don't have an email, open a popup to purpose to add an email.
 * The user can choose to add an email or cancel and close the popup.
 */
instance.web.form.FieldMany2ManyTagsEmail = instance.web.form.FieldMany2ManyTags.extend({

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
        new instance.web.Model('res.partner').call("search", [[
                ["id", "in", ids], 
                ["email", "=", false], 
                ["notification_email_send", "in", ['all', 'comment']] ]], 
                {context: this.build_context()})
            .then(function (record_ids) {
                // valid partner
                var valid_partner = _.difference(ids, record_ids);
                self.values = self.values.concat(valid_partner);
                self.values_checking = _.difference(self.values_checking, valid_partner);

                // unvalid partner
                _.each(record_ids, function (id) {
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
instance.web.form.widgets = instance.web.form.widgets.extend({
    'many2many_tags_email' : 'instance.web.form.FieldMany2ManyTagsEmail',
});

};
