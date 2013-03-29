openerp.mail.suggestions = function(session, mail) {
    var _t = session.web._t;
    var QWeb = session.web.qweb

    var suggestions = session.suggestions = {};

    suggestions.Sidebar = session.web.Widget.extend({
        template: "mail.suggestions",
        init: function (parent, action) {
            var self = this;
            this._super(parent, action);
            this.res_user = new session.web.DataSetSearch(this, 'res.users');
        },
    });

    var removed_suggested_group = session.removed_suggested_group = [];
    suggestions.Groups = session.web.Widget.extend({
        init: function (parent, action) {
            console.log("init");
            var self = this;
            this._super(parent, action);
            this.deferred = $.Deferred();
            this.mail_group = new session.web.DataSetSearch(this, 'mail.group');
            this.suggestions = [];
        },
        start: function() {
            var self = this;
            var args = arguments;
            var res = self.get_suggested_group();
            return $.when(res).done(function() {});
        },
        get_suggested_group: function () {
            
            var self = this;
            var group = self.mail_group.call('get_suggested_thread', {'removed_suggested_threads':removed_suggested_group}).then(function(res) {
                if(res.length<=0) {self.$(".oe_user_profile_group").hide();}
                _(res).each(function(result) {
                    result['image']=self.session.url('/web/binary/image', {model: 'mail.group', field: 'image_small', id: result.id});
                });
                self.suggestions = res
            });
            return $.when(group).done(function() {
                self.$el.html( QWeb.render("mail.suggestions.groups", {'widget': self}) );
                self.bind_events();
            });
        },
        bind_events: function() {
            var self = this;
            this.$el.one('click', '.oe_remove_suggested_group', {data:this}, self.remove_suggested_group);
            self.$el.one('click', '.oe_join_group', { data:self }, self.join_group);
        },
        join_group:function(event) {
            var self = this;
            console.log("join");
            return event.data.data.mail_group.call('message_subscribe_users', [[$(self).attr('id')],[event.data.data.session.uid]]).then(function(res) {
                event.data.data.get_suggested_group();
            });
        },
        remove_suggested_group: function(event) {
            var self = this;
            console.log("remove");
            removed_suggested_group.push($(self).attr('id'));
            event.data.data.get_suggested_group();
        },
    });

    mail.Wall.include({
        start: function(options) {
            this._super(options);
            var self = this;
            var sidebar = new suggestions.Sidebar(self);
            sidebar.appendTo(self.$el.find('.oe_mail_wall_aside')).then( function() {
                
            });

            var sug_groups = new suggestions.Groups(self);
            // sug_groups.replace(self.$el.find('.oe_suggestions_groups'));
            $.when(sug_groups.start()).done(function() {
                //self.$el.find('.oe_suggestions_groups').html(sug_groups.$el.html());
                sug_groups.replace( self.$el.find('.oe_suggestions_groups') );
            });
            
        }
    });

};
