openerp_mail_followers = function(session, mail) {
    var _t = session.web._t,
       _lt = session.web._lt;

    var mail_followers = session.mail_followers = {};

    /** 
     * ------------------------------------------------------------
     * mail_followers Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a list of records as a vertical
     * list, with an image on the left. The widget itself is a floatting
     * right-sided box.
     * This widget is mainly used to display the followers of records
     * in OpenChatter.
     */

    /* Add the widget to registry */
    session.web.form.widgets.add('mail_followers', 'openerp.mail_followers.Followers');

    mail_followers.Followers = session.web.form.AbstractField.extend({
        template: 'mail.followers',

        init: function() {
            this._super.apply(this, arguments);
            this.options.image = this.node.attrs.image || 'image_small';
            this.options.title = this.node.attrs.title || 'Followers';
            this.ds_model = new session.web.DataSetSearch(this, this.view.model);
            this.ds_follow = new session.web.DataSetSearch(this, this.field.relation);
        },

        start: function() {
            // use actual_mode property on view to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
            this.reinit();
            this.bind_events();
        },

        _check_visibility: function() {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
        },

        reinit: function() {
            this.message_is_follower == undefined;
            this.display_buttons();
        },

        bind_events: function() {
            var self = this;
            this.$('button.oe_mail_button_unfollow').on('click', function () { self.do_unfollow(); })
                .mouseover(function () { $(this).html('Unfollow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.$el.on('click', 'button.oe_mail_button_follow', function () { self.do_follow(); });
            this.$el.on('click', 'a.oe_mail_invite', function(event) {
                action = {
                    type: 'ir.actions.act_window',
                    res_model: 'mail.wizard.invite',
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {
                        'default_res_model': self.view.dataset.model,
                        'default_res_id': self.view.datarecord.id
                    },
                }
                self.do_action(action, function() { self.read_value(); });
            });
        },

        read_value: function() {
            var self = this;
            return this.ds_model.read_ids([this.view.datarecord.id], ['message_is_follower', 'message_follower_ids']).then(function (results) {
                self.set_value(results[0].message_follower_ids, results[0].message_is_follower);
            });
        },

        set_value: function(value_, message_is_follower) {
            this.reinit();
            if (! this.view.datarecord.id ||
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$('div.oe_mail_recthread_aside').hide();
                return;
            }
            return this.fetch_followers(value_  || this.get_value(), message_is_follower);
        },

        fetch_followers: function (value_, message_is_follower) {
            this.value = value_;
            this.message_is_follower = message_is_follower || (this.getParent().fields.message_is_follower && this.getParent().fields.message_is_follower.get_value());
            return this.ds_follow.call('read', [value_, ['name', 'user_ids']]).pipe(this.proxy('display_followers'), this.proxy('display_generic'));
        },


        /* Display generic info about follower, for people not having access to res_partner */
        display_generic: function (error, event) {
            event.preventDefault();
            var node_user_list = this.$('ul.oe_mail_followers_display').empty();
            // format content: Followers (You and 0 other) // Followers (3)
            var content = this.options.title;
            if (this.message_is_follower) {
                content += ' (You and ' + (this.value.length-1) + ' other)';
            }
            else {
                content += ' (' + this.value.length + ')'
            }
            this.$('div.oe_mail_recthread_followers h4').html(content);
            this.display_buttons();
            return $.when();
        },

        /** Display the followers, evaluate is_follower directly */
        display_followers: function (records) {
            var self = this;
            var node_user_list = this.$('ul.oe_mail_followers_display').empty();
            this.$('div.oe_mail_recthread_followers h4').html(this.options.title + ' (' + records.length + ')');
            _(records).each(function (record) {
                record.avatar_url = mail.ChatterUtils.get_image(self.session, 'res.partner', 'image_small', record.id);
                $(session.web.qweb.render('mail.followers.partner', {'record': record})).appendTo(node_user_list);
            });
            this.display_buttons();
        },

        display_buttons: function () {
            this.$('button.oe_mail_button_follow').hide();
            this.$('button.oe_mail_button_unfollow').hide();
            this.$('span.oe_mail_invite_wrapper').hide();
            if (! this.view.is_action_enabled('edit')) return;
            this.$('span.oe_mail_invite_wrapper').show();
            if (this.message_is_follower) { this.$('button.oe_mail_button_unfollow').show(); }
            else if (this.message_is_follower == false) { this.$('button.oe_mail_button_follow').show(); }
        },

        do_follow: function () {
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id], undefined, context]).pipe(this.proxy('read_value'));
        },

        do_unfollow: function () {
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_unsubscribe_users', [[this.view.datarecord.id], undefined, context]).pipe(this.proxy('read_value'));
        },
    });
};
