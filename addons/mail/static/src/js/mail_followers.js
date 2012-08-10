openerp_mail_followers = function(session, mail) {
    var _t = session.web._t,
       _lt = session.web._lt;

    var mail_followers = session.mail_followers = {};

    /** 
     * ------------------------------------------------------------
     * mail_thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of the Chatter on documents.
     */

    /* Add mail_thread widget to registry */
    session.web.form.widgets.add('mail_followers', 'openerp.mail_followers.Followers');

    /** mail_thread widget: thread of comments */
    mail_followers.Followers = session.web.form.AbstractField.extend({
        // QWeb template to use when rendering the object
        template: 'mail.followers',

       init: function() {
            this._super.apply(this, arguments);
            this.params = this.get_definition_options();
            this.params.see_subscribers = true;
            this.params.see_subscribers_options = this.params.see_subscribers_options || false;
            this.ds = new session.web.DataSetSearch(this, this.view.model);
            this.ds_users = new session.web.DataSetSearch(this, 'res.users');

        },
        
        start: function() {
            var self = this;

            // NB: all the widget should be modified to check the actual_mode property on view, not use
            // any other method to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
            
            // session.mail.ChatterUtils.bind_events(this);
            this.$element.find('button.oe_mail_button_followers').click(function () { self.do_toggle_followers(); });
            if (! this.params.see_subscribers_options) {
                this.$element.find('button.oe_mail_button_followers').hide(); }
            this.$element.find('button.oe_mail_button_follow').click(function () { self.do_follow(); })
                .mouseover(function () { $(this).html('Follow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Not following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.$element.find('button.oe_mail_button_unfollow').click(function () { self.do_unfollow(); })
                .mouseover(function () { $(this).html('Unfollow').removeClass('oe_mail_button_mouseout').addClass('oe_mail_button_mouseover'); })
                .mouseleave(function () { $(this).html('Following').removeClass('oe_mail_button_mouseover').addClass('oe_mail_button_mouseout'); });
            this.reinit();
        },
        
        _check_visibility: function() {
            this.$element.toggle(this.view.get("actual_mode") !== "create");
        },
        
        destroy: function () {
            this._super.apply(this, arguments);
        },
        
        reinit: function() {
            this.params.see_subscribers = true;
            this.params.see_subscribers_options = this.params.see_subscribers_options || false;
            this.$element.find('button.oe_mail_button_followers').html('Hide followers')
            this.$element.find('button.oe_mail_button_follow').hide();
            this.$element.find('button.oe_mail_button_unfollow').hide();
        },
        
        set_value: function(value_) {
            console.log(value_);
            // debugger
            this.reinit();
            if (! this.view.datarecord.id ||
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$element.find('div.oe_mail_recthread_aside').hide();
                return;
            }
            return this.fetch_subscribers(value_);
        },
        
        fetch_subscribers: function (value_) {
            return this.ds_users.call('read', [value_ || this.get_value(), ['name', 'image_small']]).then(this.proxy('display_subscribers'));
        },
        
        display_subscribers: function (records) {
            var self = this;
            this.is_subscriber = false;
            var user_list = this.$element.find('ul.oe_mail_followers_display').empty();
            this.$element.find('div.oe_mail_recthread_followers h4').html('Followers (' + records.length + ')');
            _(records).each(function (record) {
                if (record.id == self.session.uid) { self.is_subscriber = true; }
                record.avatar_url = mail.ChatterUtils.get_image(self.session.prefix, self.session.session_id, 'res.users', 'image_small', record.id);
                $(session.web.qweb.render('mail.followers.partner', {'record': record})).appendTo(user_list);
            });
            if (this.is_subscriber) {
                this.$element.find('button.oe_mail_button_follow').hide();
                this.$element.find('button.oe_mail_button_unfollow').show(); }
            else {
                this.$element.find('button.oe_mail_button_follow').show();
                this.$element.find('button.oe_mail_button_unfollow').hide(); }
        },
        
        do_follow: function () {
            return this.ds.call('message_subscribe', [[this.view.datarecord.id]]).pipe(this.proxy('fetch_subscribers'));
        },
        
        do_unfollow: function () {
            var self = this;
            return this.ds.call('message_unsubscribe', [[this.view.datarecord.id]]).pipe(function (record) {
                // debugger
                var new_value = self.view.datarecord.message_subscriber_ids;
                // return [new_value.splice(_.indexOf(new_value, self.session.uid, true), 1);]
                return [2]
                }).pipe(this.proxy('set_value'));
        },
        
        do_toggle_followers: function () {
            this.params.see_subscribers = ! this.params.see_subscribers;
            if (this.params.see_subscribers) { this.$element.find('button.oe_mail_button_followers').html('Hide followers'); }
            else { this.$element.find('button.oe_mail_button_followers').html('Show followers'); }
            this.$element.find('div.oe_mail_recthread_followers').toggle();
        },
    });
};
