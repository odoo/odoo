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
            this.options.image = this.node.attrs.image || 'image_small';
            this.options.title = this.node.attrs.title || 'Followers';
            this.ds_model = new session.web.DataSetSearch(this, this.view.model);
            this.ds_follow = new session.web.DataSetSearch(this, this.field.relation);
        },

        start: function() {
            var self = this;
            // NB: all the widget should be modified to check the actual_mode property on view, not use
            // any other method to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
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
            this.$element.find('button.oe_mail_button_follow').hide();
            this.$element.find('button.oe_mail_button_unfollow').hide();
        },

        set_value: function(value_) {
            this.reinit();
            if (! this.view.datarecord.id ||
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$element.find('div.oe_mail_recthread_aside').hide();
                return;
            }
            if (this.getParent().fields.message_is_follower === undefined) {
                // TDE: raise a warning
            }
            this.message_is_follower = this.getParent().fields.message_is_follower.get_value();
            console.log(this.message_is_follower);
            return this.fetch_followers(value_);
        },

        fetch_followers: function (value_) {
            return this.ds_follow.call('read', [value_ || this.get_value(), ['name']]).then(this.proxy('display_followers'));
        },

        /**
         * Display the followers.
         * TODO: replace the is_follower check by fields read */
        display_followers: function (records) {
            var self = this;
            var node_user_list = this.$element.find('ul.oe_mail_followers_display').empty();
            this.$element.find('div.oe_mail_recthread_followers h4').html(this.options.title + ' (' + records.length + ')');
            _(records).each(function (record) {
                record.avatar_url = mail.ChatterUtils.get_image(self.session.prefix, self.session.session_id, 'res.partner', 'image_small', record.id);
                $(session.web.qweb.render('mail.followers.partner', {'record': record})).appendTo(node_user_list);
            });
            if (this.message_is_follower) {
                this.$element.find('button.oe_mail_button_follow').hide();
                this.$element.find('button.oe_mail_button_unfollow').show(); }
            else {
                this.$element.find('button.oe_mail_button_follow').show();
                this.$element.find('button.oe_mail_button_unfollow').hide(); }
        },

        do_follow: function () {
            return this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id]]).pipe(this.proxy('set_value'));
        },

        do_unfollow: function () {
            return this.ds_model.call('message_unsubscribe_users', [[this.view.datarecord.id]]).pipe(this.proxy('set_value'));
        },
    });
};
