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
            this.fetch_subtype();
            this.reinit();
            this.bind_events();
        },

        _check_visibility: function() {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
            if (this.view.get("actual_mode") !== "create"){this.fetch_subtype();}
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
            this.$el.on('click', 'button.oe_mail_button_follow', function () { self.do_follow(); self.fetch_subtype(); });
            this.$el.on('click','ul.oe_mail_recthread_subtype', function () {self.update_subtype();})
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
            return this.ds_model.read_ids([this.view.datarecord.id], ['message_follower_ids']).pipe(function (results) {
                return results[0].message_follower_ids;
            }).pipe(this.proxy('set_value'));
        },

        set_value: function(value_) {
            this.reinit();
            if (! this.view.datarecord.id ||
                session.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$el.find('div.oe_mail_recthread_aside').hide();
                return;
            }
            return this.fetch_followers(value_  || this.get_value());
        },

        fetch_followers: function (value_) {
            return this.ds_follow.call('read', [value_, ['name', 'user_ids']]).pipe(this.proxy('display_followers'));
        },

        /** Display the followers, evaluate is_follower directly */
        display_followers: function (records) {
            var self = this;
            this.message_is_follower = _.indexOf(_.flatten(_.pluck(records, 'user_ids')), this.session.uid) != -1;
            var node_user_list = this.$el.find('ul.oe_mail_followers_display').empty();
            this.$el.find('div.oe_mail_recthread_followers h4').html(this.options.title + ' (' + records.length + ')');
            _(records).each(function (record) {
                record.avatar_url = mail.ChatterUtils.get_image(self.session, 'res.partner', 'image_small', record.id);
                $(session.web.qweb.render('mail.followers.partner', {'record': record})).appendTo(node_user_list);
            });
            if (this.message_is_follower) {
                this.$el.find('button.oe_mail_button_follow').hide();
                this.$el.find('button.oe_mail_button_unfollow').show(); 
                this.$el.find('ul.oe_mail_recthread_subtype').show(); }
            else {
                this.$el.find('button.oe_mail_button_follow').show();
                this.$el.find('button.oe_mail_button_unfollow').hide();
                this.$el.find('ul.oe_mail_recthread_subtype').hide() 
                }
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
            var subtype_list = this.$el.find('ul.oe_mail_recthread_subtype').empty();
            var follower_ids = this.follower_model.call('search',[[['res_model','=',this.ds_model.model],['res_id','=',this.view.datarecord.id]]])
            follower_ids.then(function (record){
                var follower_read = self.follower_model.call('read',  [record,['subtype_ids']]);
                follower_read.then(function (follower_record){
                    if(follower_record.length != 0){
                        _(follower_record[0].subtype_ids).each(function (subtype_id){
                            var subtype_check = self.$el.find('.oe_msg_subtype_check[id=' + subtype_id + ']')
                            if(subtype_check.length > 0){
                                subtype_check[0].checked=true}
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
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id], undefined, context]).pipe(this.proxy('read_value'));
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
            var context = new session.web.CompoundContext(this.build_context(), {});
            return this.ds_model.call('message_unsubscribe_users', [[this.view.datarecord.id], undefined, context]).pipe(this.proxy('read_value'));
        },
    });
};
