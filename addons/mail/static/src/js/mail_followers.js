openerp_mail_followers = function(session, mail) {
    var _t = session.web._t,
       _lt = session.web._lt;

    var mail_followers = session.mail_followers = {};

    /** 
     * ------------------------------------------------------------
     * mail_followers Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a list of records as a vetical
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
            this.params = {};
            this.params.image = this.node.attrs.image || 'image_small';
            this.params.title = this.node.attrs.title || 'Followers';
            this.params.display_followers = true;
            this.params.display_control = this.node.attrs.display_control || false;
            this.params.display_actions = this.node.attrs.display_actions || false;
            this.ds_model = new session.web.DataSetSearch(this, this.view.model);
            this.sub_model = new session.web.DataSetSearch(this,'mail.message.subtype')
            this.ds_follow = new session.web.DataSetSearch(this, this.field.relation);
            this.follower_model = new session.web.DataSetSearch(this,'mail.followers')
        },

        start: function() {
            var self = this;
            // NB: all the widget should be modified to check the actual_mode property on view, not use
            // any other method to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
            this.fetch_subtype();
            this.$el.find('div.oe_mail_recthread_subtype').click(function () {self.update_subtype();})
            this.$el.find('button.oe_mail_button_followers').click(function () { self.do_toggle_followers(); });

            if (! this.params.display_control) {
                this.$el.find('button.oe_mail_button_followers').hide();
                this.$el.find('div.oe_mail_recthread_subtype').hide()
            }
            this.$el.find('button.oe_mail_button_follow').click(function () {
                self.do_follow();
                self.fetch_subtype();
                })
                .mouseover(function () { $(this).html('Follow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Not following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.$el.find('button.oe_mail_button_unfollow').click(function () { self.do_unfollow(); })
                .mouseover(function () { $(this).html('Unfollow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.reinit();
        },

        _check_visibility: function() {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
            if (this.view.get("actual_mode") !== "create"){this.fetch_subtype();}
        },

        destroy: function () {
            this._super.apply(this, arguments);
        },

        reinit: function() {
            this.params.display_followers = true;
            this.params.display_control = this.node.attrs.display_control || false;
            this.params.display_actions = this.node.attrs.display_actions || false;
            this.$el.find('button.oe_mail_button_followers').html('Hide followers')
            this.$el.find('button.oe_mail_button_follow').hide();
            this.$el.find('button.oe_mail_button_unfollow').hide();
            this.$el.find('div.oe_mail_recthread_subtype').hide()
        },

        set_value: function(value_) {
            this.reinit();
            if (! this.view.datarecord.id ||
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$el.find('div.oe_mail_recthread_aside').hide();
                return;
            }
            return this.fetch_subscribers(value_);
        },

        fetch_subscribers: function (value_) {
            return this.ds_follow.call('read', [value_ || this.get_value(), ['name', this.params.image]]).then(this.proxy('display_subscribers'));
        },

        /**
         * Display the followers.
         * TODO: replace the is_subscriber check by fields read */
        display_subscribers: function (records) {
            var self = this;
            this.is_subscriber = false;
            //if (self.view.get("actual_mode") === "edit"){self.fetch_subtype();}
            var user_list = this.$el.find('ul.oe_mail_followers_display').empty();
            this.$el.find('div.oe_mail_recthread_followers h4').html(this.params.title + ' (' + records.length + ')');
            _(records).each(function (record) {
                if (record.id == self.session.uid) { self.is_subscriber = true; }
                record.avatar_url = mail.ChatterUtils.get_image(self.session.prefix, self.session.session_id, 'res.users', 'image_small', record.id);
                $(session.web.qweb.render('mail.followers.partner', {'record': record})).appendTo(user_list);
            });
            if (this.is_subscriber) {
                this.$el.find('button.oe_mail_button_follow').hide();
                this.$el.find('button.oe_mail_button_unfollow').show(); 
                this.$el.find('div.oe_mail_recthread_subtype').show(); }
            else {
                this.$el.find('button.oe_mail_button_follow').show();
                this.$el.find('button.oe_mail_button_unfollow').hide();
                this.$el.find('div.oe_mail_recthread_subtype').hide() }
        },
        update_subtype: function (){
            var self = this;
            var cheklist = new Array();
            _(this.$el.find('.oe_msg_subtype_check')).each(function(record){
                if($(record).is(':checked')) {
                    cheklist.push(parseInt($(record).attr('id')))}
            });
            self.ds_model.call('message_subscribe_udpate_subtypes',[[self.view.datarecord.id],[self.session.uid],cheklist])
        },
        // Display the subtypes of each records.
        display_subtype: function(records) {
            var self = this
            var subtype_list = this.$el.find('div.oe_mail_recthread_subtype').empty();
            var follower_ids = this.follower_model.call('search',[[['res_model','=',this.ds_model.model],['res_id','=',this.view.datarecord.id],['user_id','=',this.session.uid]]])
            follower_ids.then(function (record){
                var follower_read = self.follower_model.call('read',  [record,['subtype_ids']]);
                follower_read.then(function (follower_record){
                    if(follower_record.length != 0){
                        _(follower_record[0].subtype_ids).each(function (subtype_id){
                            self.$el.find('.oe_msg_subtype_check[id=' + subtype_id + ']')[0].checked=true
                        });
                    }
                })
            });
            _(records).each(function (record) {
                record.name = record.name.toLowerCase().replace(/\b[a-z]/g, function(letter) {return letter.toUpperCase();});
                $(session.web.qweb.render('mail.record_thread.subtype', {'record': record})).appendTo(subtype_list);
            });
        },
            
        do_follow: function () {
            return this.ds_model.call('message_subscribe', [[this.view.datarecord.id]]).pipe(this.proxy('set_value'));
        },
        
        //fetch subtype from subtype model
        fetch_subtype: function () {
            var self = this
            var subtype_object = this.sub_model.call('search', [[['model_ids.model','=',this.view.model]]]);
            subtype_object.then(function (subtype_ids){
                self.sub_model.call('read',  [subtype_ids || self.get_value(),['name', 'default']]).then(self.proxy('display_subtype'));
            });
        },

        do_unfollow: function () {
            return this.ds_model.call('message_unsubscribe', [[this.view.datarecord.id]]).pipe(this.proxy('set_value'));
        },

        do_toggle_followers: function () {
            this.params.see_subscribers = ! this.params.see_subscribers;
            if (this.params.see_subscribers) { this.$el.find('button.oe_mail_button_followers').html('Hide followers'); }
            else { this.$el.find('button.oe_mail_button_followers').html('Show followers'); }
            this.$el.find('div.oe_mail_recthread_followers').toggle();
        },
    });
};
