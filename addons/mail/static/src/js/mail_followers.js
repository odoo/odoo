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
            this.image = this.node.attrs.image || 'image_small';
            this.comment = this.node.attrs.help || false;
            this.displayed_limit = this.node.attrs.displayed_nb || 10;
            this.displayed_nb = this.displayed_limit;
            this.ds_model = new session.web.DataSetSearch(this, this.view.model);
            this.ds_users = new session.web.DataSetSearch(this, 'res.users');

            this.value = [];
            this.followers = [];
            
            this.view_is_editable = this.__parentedParent.is_action_enabled('edit');
        },

        start: function() {
            // use actual_mode property on view to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this.on_check_visibility_mode);
            this.on_check_visibility_mode();
            this.reinit();
            this.bind_events();
            this._super();
        },

        on_check_visibility_mode: function () {
            this.set({"force_invisible": this.view.get("actual_mode") == "create"});
        },

        set_value: function(_value) {
            this.value = _value;
            this._super(_value);
        },

        reinit: function() {
            this.message_is_follower == undefined;
            this.display_buttons();
        },

        bind_events: function() {
            var self = this;
            // event: click on '(Un)Follow' button, that toggles the follow for uid
            this.$('.oe_follower').on('click', function (event) {
                if($(this).hasClass('oe_notfollow'))
                    self.do_follow();
                else
                    self.do_unfollow();
            });
            // event: click on a subtype, that (un)subscribe for this subtype
            this.$el.on('click', '.oe_subtype_list input', function(event) {
                self.do_update_subscription(event);
                var $list = self.$('.oe_subtype_list');
                if(!$list.hasClass('open')) {
                    $list.addClass('open');
                }
                if(self.$('.oe_subtype_list ul')[0].children.length < 1) {
                    $list.removeClass('open');
                }
                event.stopPropagation();
            });
            // event: click on 'invite' button, that opens the invite wizard
            this.$('.oe_invite').on('click', self.on_invite_follower);
            // event: click on 'edit_subtype(pencil)' button to edit subscription
            this.$el.on('click', '.oe_edit_subtype', self.on_edit_subtype);
            this.$el.on('click', '.oe_remove_follower', self.on_remove_follower);
            this.$el.on('click', '.oe_show_more', self.on_show_more_followers);
            this.$el.on('click', 'a[data-partner]', self.on_follower_clicked);
        },

        on_edit_subtype: function(event) {
            var self = this;
            var $currentTarget = $(event.currentTarget);
            var user_pid = $currentTarget.data('id');
            $('div.oe_edit_actions').remove();
            self.$dialog = new session.web.Dialog(this, {
                            size: 'small',
                            title: _t('Edit Subscription of ') + $currentTarget.siblings('a').text(),
                            buttons: [
                                    { text: _t("Apply"), click: function() { 
                                        self.do_update_subscription(event, user_pid);
                                        this.parents('.modal').modal('hide');
                                    }},
                                    { text: _t("Cancel"), click: function() { this.parents('.modal').modal('hide'); }}
                                ],
                    }, "<div class='oe_edit_actions'>").open();
            return self.fetch_subtypes(user_pid);
        },

        on_invite_follower: function (event) {
            var self = this;
            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.wizard.invite',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                name: _t('Invite Follower'),
                target: 'new',
                context: {
                    'default_res_model': this.view.dataset.model,
                    'default_res_id': this.view.datarecord.id,
                },
            }
            this.do_action(action, {
                on_close: function() {
                    self.read_value();
                },
            });
        },

        on_show_more_followers: function (event) {
            this.displayed_nb += this.displayed_limit;
            this.display_followers(false);
        },

        on_remove_follower: function (event) {
            var partner_id = $(event.target).data('id');
            var name = $(event.target).parent().find("a").html();
            if (confirm(_.str.sprintf(_t("Warning! \n %s won't be notified of any email or discussion on this document. Do you really want to remove him from the followers ?"), name))) {
                var context = new session.web.CompoundContext(this.build_context(), {});
                return this.ds_model.call('message_unsubscribe', [[this.view.datarecord.id], [partner_id], context])
                    .then(this.proxy('read_value'));
            }
        },

        on_follower_clicked: function  (event) {
            event.preventDefault();
            var partner_id = $(event.target).data('partner');
            var state = {
                'model': 'res.partner',
                'id': partner_id,
                'title': this.record_name
            };
            session.webclient.action_manager.do_push_state(state);
            var action = {
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: 'res.partner',
                views: [[false, 'form']],
                res_id: partner_id,
            }
            this.do_action(action);
        },

        read_value: function () {
            var self = this;
            this.displayed_nb = this.displayed_limit;
            return this.ds_model.read_ids([this.view.datarecord.id], ['message_follower_ids']).then(function (results) {
                self.value = results[0].message_follower_ids;
                self.render_value();
            });
        },

        render_value: function () {
            this.reinit();
            return this.fetch_followers(this.value);
        },

        fetch_followers: function (value_) {
            this.value = value_ || [];
            return this.ds_model.call('read_followers_data', [this.value])
                .then(this.proxy('display_followers'), this.proxy('fetch_generic'))
                .then(this.proxy('display_buttons'))
                .then(this.proxy('fetch_subtypes'));
        },

        /** Read on res.partner failed: fall back on a generic case
            - fetch current user partner_id (call because no other smart solution currently) FIXME
            - then display a generic message about followers */
        fetch_generic: function (error, event) {
            var self = this;
            event.preventDefault();
            return this.ds_users.call('read', [[this.session.uid], ['partner_id']]).then(function (results) {
                var pid = results[0]['partner_id'][0];
                self.message_is_follower = (_.indexOf(self.value, pid) != -1);
            }).then(self.proxy('display_generic'));
        },

        _format_followers: function(count){
            var str = '';
            if(count <= 0){
                str = _t('No followers');
            }else if(count === 1){
                str = _t('One follower');
            }else{
                str = ''+count+' '+_t('followers');
            }
            return str;
        },

        /* Display generic info about follower, for people not having access to res_partner */
        display_generic: function () {
            var self = this;
            var node_user_list = this.$('.oe_follower_list').empty();
            this.$('.oe_follower_title').html(this._format_followers(this.value.length));
        },

        /** Display the followers */
        display_followers: function (records) {
            var self = this;
            this.message_is_follower = false;
            this.followers = records || this.followers;
            // clean and display title
            var node_user_list = this.$('.oe_follower_list').empty();
            this.$('.oe_follower_title').html(this._format_followers(this.followers.length));
            self.message_is_follower = _.indexOf(this.followers.map(function (rec) { return rec[2]['is_uid']}), true) != -1;
            // truncate number of displayed followers
            var truncated = this.followers.slice(0, this.displayed_nb);
            _(truncated).each(function (record) {
                partner = {
                    'id': record[0],
                    'name': record[1],
                    'is_uid': record[2]['is_uid'],
                    'is_editable': record[2]['is_editable'],
                    'avatar_url': mail.ChatterUtils.get_image(self.session, 'res.partner', 'image_small', record[0]),
                }
                $(session.web.qweb.render('mail.followers.partner', {'record': partner, 'widget': self})).appendTo(node_user_list);
                // On mouse-enter it will show the edit_subtype pencil.
                if (partner.is_editable) {
                    self.$('.oe_follower_list').on('mouseenter mouseleave', function(e) {
                        self.$('.oe_edit_subtype').toggleClass('oe_hidden', e.type == 'mouseleave');
                        self.$('.oe_follower_list').find('.oe_partner').toggleClass('oe_partner_name', e.type == 'mouseenter');
                    });
                }
            });
            // FVA note: be sure it is correctly translated
            if (truncated.length < this.followers.length) {
                $(session.web.qweb.render('mail.followers.show_more', {'number': (this.followers.length - truncated.length)} )).appendTo(node_user_list);
            }
        },

        display_buttons: function () {
            if (this.message_is_follower) {
                this.$('button.oe_follower').removeClass('oe_notfollow').addClass('oe_following');
            }
            else {
                this.$('button.oe_follower').removeClass('oe_following').addClass('oe_notfollow');
            }

            if (this.view.is_action_enabled('edit'))
                this.$('span.oe_mail_invite_wrapper').hide();
            else
                this.$('span.oe_mail_invite_wrapper').show();
        },

        /** Fetch subtypes, only if current user is follower */
        fetch_subtypes: function (user_pid) {
            var self = this;
            var dialog = false;
            if (user_pid) {
                dialog = true;
            } else {
                var subtype_list_ul = this.$('.oe_subtype_list ul').empty();
                if (! this.message_is_follower) {
                    this.$('.oe_subtype_list > .dropdown-toggle').attr('disabled', true);
                    return;
                }
                else {
                    this.$('.oe_subtype_list > .dropdown-toggle').attr('disabled', false);
                }
            }
            var id = this.view.datarecord.id;
            this.ds_model.call('message_get_subscription_data', [[id], user_pid, new session.web.CompoundContext(this.build_context(), {})])
                .then(function (data) {self.display_subtypes(data, id, dialog);});
        },

        /** Display subtypes: {'name': default, followed} */
        display_subtypes:function (data, id, dialog) {
            var self = this;
            if (dialog) {
                var $list = self.$dialog.$el;
            }
            else {
                var $list = this.$('.oe_subtype_list ul');
            }
            var records = data[id].message_subtype_data;
            this.records_length = $.map(records, function(value, index) { return index; }).length;
            if (this.records_length > 1) { self.display_followers(); }
            var old_model = '';
            _(records).each(function (record, record_name) {
                if (old_model != record.parent_model){
                    if (old_model != ''){
                        var index = $($list).find('.oe_subtype').length;
                        $($($list).find('.oe_subtype')[index-1]).addClass('subtype-border');
                    }
                    old_model = record.parent_model;
                }
                record.name = record_name;
                record.followed = record.followed || undefined;
                $(session.web.qweb.render('mail.followers.subtype', {'record': record, 'dialog': dialog})).appendTo($list);
            });
        },

        do_follow: function () {
            var context = new session.web.CompoundContext(this.build_context(), {});
            this.$('.oe_subtype_list > .dropdown-toggle').attr('disabled', false);
            this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id], [this.session.uid], undefined, context])
                .then(this.proxy('read_value'));

            _.each(this.$('.oe_subtype_list input'), function (record) {
                $(record).attr('checked', 'checked');
            });
        },
        
        do_unfollow: function (user_pid) {
            var self = this;
            if (confirm(_t("Warning! \nYou won't be notified of any email or discussion on this document. Do you really want to unfollow this document ?"))) {
                _(this.$('.oe_msg_subtype_check')).each(function (record) {
                    $(record).attr('checked',false);
                });
            var action_unsubscribe = 'message_unsubscribe_users';
            this.$('.oe_subtype_list > .dropdown-toggle').attr('disabled', true);
            var follower_ids = [this.session.uid];
            if (user_pid) {
                action_unsubscribe = 'message_unsubscribe';
                follower_ids = [user_pid];
            }
                var context = new session.web.CompoundContext(this.build_context(), {});
                return this.ds_model.call(action_unsubscribe, [[this.view.datarecord.id], follower_ids, context])
                     .then(this.proxy('read_value'));
            }
            return false;
        },

        do_update_subscription: function (event, user_pid) {
            var self = this;

            var action_subscribe = 'message_subscribe_users';
            var follower_ids = [this.session.uid];
            var oe_action = this.$('.oe_actions input[type="checkbox"]');
            if (user_pid) {
                action_subscribe = 'message_subscribe';
                follower_ids = [user_pid];
                oe_action = $('.oe_edit_actions input[type="checkbox"]');
            }
            var checklist = new Array();
            _(oe_action).each(function (record) {
                if ($(record).is(':checked')) {
                    checklist.push(parseInt($(record).data('id')));
                }
            });

            if (!checklist.length) {
                if (!this.do_unfollow(user_pid)) {
                    $(event.target).attr("checked", "checked");
                } else {
                      self.$('.oe_subtype_list ul').empty(); 
                }
            } else {
                var context = new session.web.CompoundContext(this.build_context(), {});
                return this.ds_model.call(action_subscribe, [[this.view.datarecord.id], follower_ids, checklist, context])
                    .then(this.proxy('read_value'));
            }
        },
    });
};
