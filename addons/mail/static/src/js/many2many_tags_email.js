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
        var self = this;
        // filter for removed values
        var values_removed = _.difference(self.values, self.get('value'));

        if (values_removed.length) {
            self.values = _.difference(self.values, values_removed);
            this.set({'value': self.values});
            return false;
        }

        // find not checked values
        var not_checked = _.difference(self.get('value'), self.values);

        // find not checked values and not on checking
        var not_checked = _.difference(not_checked, self.values_checking);

        _.each(not_checked, function (val, key) {
            self.values_checking.push(val);
            self._check_email_popup(val);
        });
    },

    _check_email_popup: function (id) {
        var self = this;
        new instance.web.Model('res.partner').call("read", [id, ["email", "notification_email_send"]], {context: this.build_context()})
            .pipe(function (dict) {
                if (!dict.email && (dict.notification_email_send == 'all' || dict.notification_email_send == 'comment')) {
                    var pop = new instance.web.form.FormOpenPopup(self);
                    pop.show_element(
                        'res.partner',
                        dict.id,
                        self.build_context(),
                        {
                            title: _t("Please complete partner's informations and Email"),
                        }
                    );
                    pop.on('write_completed', self, function () {
                        self._checked(dict.id, true);
                    });
                    pop.on('closed', self, function () {
                        self._checked(dict.id, false);
                    });
                } else {
                    self._checked(dict.id, true);
                }
            });
    },

    _checked: function (id, access) {
        if (access) {
            this.values.push(id);
        }
        this.values_checking = _.without(this.values_checking, id);
        this.set({'value': this.values});
    },
});


/**
 * Registry of form fields
 */
instance.web.form.widgets = instance.web.form.widgets.extend({
    'many2many_tags_email' : 'instance.web.form.FieldMany2ManyTagsEmail',
});

};