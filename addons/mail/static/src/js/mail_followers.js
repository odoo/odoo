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
            this.sub_model = new session.web.DataSetSearch(this,'mail.message.subtype')
            this.ds_follow = new session.web.DataSetSearch(this, this.field.relation);
            this.follower_model = new session.web.DataSetSearch(this,'mail.followers')
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
            this.$el.find('button.oe_mail_button_follow').hide();
            this.$el.find('button.oe_mail_button_unfollow').hide();
        },

        bind_events: function() {
            var self = this;
            this.$('button.oe_mail_button_unfollow').on('click', function () { self.do_unfollow(); })
                .mouseover(function () { $(this).html('Unfollow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.$el.on('click', 'button.oe_mail_button_follow', function () { self.do_follow(); });
            this.$el.on('click', 'ul.oe_mail_subtypes', function () {self.do_update_subscription(); })
            this.$el.on('click', 'button.oe_mail_button_invite', function(event) {
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
            return this.ds_model.read_ids([this.view.datarecord.id], ['message_follower_ids', 'message_is_follower', 'message_subtype_data']).pipe(function (results) {
                self.set_value(results[0].message_follower_ids, results[0].message_is_follower, results[0].message_subtype_data);
            });
        },

        get_or_set: function(field_name, value) {
            if (this.view.fields[field_name]) {
                if (value !== undefined) {
                    this.view.fields[field_name].set_value(value);
                }
                return this.view.fields[field_name].get_value();
            }
            else {
                return value;
            }
        },

        set_value: function(value_, message_is_follower_value_, message_subtype_data_value_) {
            this.reinit();
            if (! this.view.datarecord.id ||
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$el.find('div.oe_mail_recthread_aside').hide();
                return;
            }
            this.message_is_follower_value_ = this.get_or_set('message_is_follower', message_is_follower_value_) || false;
            this.message_subtype_data_value_ = this.get_or_set('message_subtype_data', message_subtype_data_value_) || {};
            return this.fetch_followers(value_  || this.get_value());
        },

        fetch_followers: function (value_) {
            return this.ds_follow.call('read', [value_, ['name']]).pipe(this.proxy('display_followers'));
        },

        /** Display the followers, evaluate is_follower directly */
        display_followers: function (records) {
            var self = this;
            var node_user_list = this.$el.find('ul.oe_mail_followers_display').empty();
            this.$el.find('div.oe_mail_recthread_followers h4').html(this.options.title + ' (' + records.length + ')');
            _(records).each(function (record) {
                record.avatar_url = mail.ChatterUtils.get_image(self.session, 'res.partner', 'image_small', record.id);
                $(session.web.qweb.render('mail.followers.partner', {'record': record})).appendTo(node_user_list);
            });
            if (this.message_is_follower_value_) {
                this.$el.find('button.oe_mail_button_follow').hide();
                this.$el.find('button.oe_mail_button_unfollow').show();
            }
            else {
                this.$el.find('button.oe_mail_button_follow').show();
                this.$el.find('button.oe_mail_button_unfollow').hide();
            }
            return this.display_subtypes(this.message_subtype_data_value_);
        },

        /** Display subtypes: {'name': default, followed} */
        display_subtypes: function (records) {
            if (! this.message_is_follower_value_) {
                this.$('div.oe_mail_recthread_subtypes').remove();
                return;
            }
            var subtype_list = this.$el.find('ul.oe_mail_subtypes').empty();
            _(records).each(function (record, record_name) {
                record.name = record_name;
                record.followed = record.followed || undefined;
                $(session.web.qweb.render('mail.followers.subtype', {'record': record})).appendTo(subtype_list);
            });
        },
            
        do_follow: function () {
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id], undefined, undefined, context]).pipe(this.proxy('read_value'));
        },

        do_unfollow: function () {
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_unsubscribe_users', [[this.view.datarecord.id], undefined, context]).pipe(this.proxy('read_value'));
        },

        do_update_subscription: function () {
            var context = new session.web.CompoundContext(this.build_context(), {});
            var self = this;
            var checklist = new Array();
            _(this.$el.find('.oe_msg_subtype_check')).each(function(record){
                if($(record).is(':checked')) {
                    checklist.push(parseInt($(record).attr('id')))}
            });
            return this.ds_model.call('message_subscribe_users',[[self.view.datarecord.id], undefined, checklist, context]).pipe(this.proxy('read_value'));
        },

    });
};
