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
            this.sub_model = new session.web.DataSetSearch(this,'mail.message.subtype');
            this.ds_follow = new session.web.DataSetSearch(this, this.field.relation);
            this.follower_model = new session.web.DataSetSearch(this,'mail.followers');
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
            this.$('div.oe_mouse_subtypes')
                .on('mouseover', function () {
                    $(this).removeClass('oe_mouseout').addClass('oe_mouseover');
                    self.display_subtypes();
                })
                .on('mouseleave', function () {
                    $(this).removeClass('oe_mouseover').addClass('oe_mouseout');
                    self.display_subtypes();
                });

            this.$('button.oe_follower')
                .on('click', function () {
                    if($(this).hasClass('oe_notfollow'))
                        self.do_follow();
                    else
                        self.do_unfollow();
                })
                .on('mouseover', function () {
                    $(this).removeClass('oe_mouseout').addClass('oe_mouseover');
                })
                .on('mouseleave', function () {
                    $(this).removeClass('oe_mouseover').addClass('oe_mouseout');
                });

            this.$el.on('click', 'ul.oe_subtypes input', function () { self.do_update_subscription(); })

            this.$el.on('click', 'button.oe_invite', function(event) {
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
            return this.ds_model.read_ids([this.view.datarecord.id], ['message_follower_ids']).pipe(function (results) {
                self.set_value(results[0].message_follower_ids);
            });
        },

        set_value: function(value_) {
            this.reinit();
            return this.fetch_followers(value_  || this.get_value());
        },

        set_is_follower: function(value_) {
            for(var i in value_){
                if(value_[i]['user_ids'][0]==this.session.uid)
                    this.message_is_follower=true;
                    this.display_buttons();
                    return true;
            }
            this.message_is_follower=false;
            this.display_buttons();
            return false;
        },

        fetch_followers: function (value_) {
            this.value = value_ || {};
            this.message_is_follower = (this.getParent().fields.message_is_follower && this.getParent().fields.message_is_follower.get_value());
            if(value_)
                return this.ds_follow.call('read', [this.value, ['name', 'user_ids']]).pipe(this.proxy('display_followers'), this.proxy('display_generic'));
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
            this.$('div.oe_mail_recthread_followers h4').html(this.options.title + (records.length>=5 ? ' (' + records.length + ')' : '') );
            console.log(records);
            for(var i=0; i<records.length&&i<5; i++) {
                var record=records[i];
                record.avatar_url = mail.ChatterUtils.get_image(self.session, 'res.partner', 'image_small', record.id);
                $(session.web.qweb.render('mail.followers.partner', {'record': record})).appendTo(node_user_list);
            }
            self.set_is_follower(records);
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

        set_subtypes:function(data){
            var self = this;
            var records = data[this.view.datarecord.id].message_subtype_data;
            _(records).each(function (record, record_name) {
                record.name = record_name;
                record.followed = record.followed || undefined;
                $(session.web.qweb.render('mail.followers.subtype', {'record': record})).appendTo( self.$('ul.oe_subtypes') );
            });
        },

        /** Display subtypes: {'name': default, followed} */
        display_subtypes: function (visible) {
            var self = this;
            var recthread_subtypes = self.$('.oe_recthread_subtypes');
            subtype_list_ul = self.$('ul.oe_subtypes');

            if(subtype_list_ul.is(":empty")) {
                var context = new session.web.CompoundContext(this.build_context(), {});
                this.ds_model.call('get_message_subtypes',[[self.view.datarecord.id], context]).pipe(this.proxy('set_subtypes'));
            }
        },
        
        do_follow: function () {
            var self =this;
            _(this.$('.oe_msg_subtype_check')).each(function(record){
                $(record).attr('checked','checked');
            });
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id], undefined, undefined, context]).pipe(function(value_){
                    self.read_value(value_);
                    if(!self.$('.oe_recthread_subtypes').is(":visible"))
                        self.display_subtypes(true);
                });
        },
        
        do_unfollow: function () {
            _(this.$('.oe_msg_subtype_check')).each(function(record){
                $(record).attr('checked',false);
            });
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_unsubscribe_users', [[this.view.datarecord.id], undefined, context]).pipe(this.proxy('read_value'));
        },

        do_update_subscription: function () {
            var context = new session.web.CompoundContext(this.build_context(), {});
            var self = this;

            var checklist = new Array();
            _(this.$('.oe_msg_subtype_check')).each(function(record){
                if($(record).is(':checked')) {
                    checklist.push(parseInt($(record).data('id')))}
            });

            if(!checklist.length)
                return this.do_unfollow();
            else
                return this.ds_model.call('message_subscribe_users',[[self.view.datarecord.id], undefined, checklist, context]).pipe(this.proxy('read_value'));
        },

    });
};