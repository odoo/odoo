openerp.mail.suggestions = function(session, mail) {
    var _t = session.web._t;
    var QWeb = session.web.qweb;

    var suggestions = session.suggestions = {};

    suggestions.Sidebar = session.web.Widget.extend({
        template: "mail.suggestions",
        init: function (parent, action) {
            var self = this;
            this._super(parent, action);
            this.res_user = new session.web.DataSetSearch(this, 'res.users');
        }
    });

    var removed_suggested_group = session.removed_suggested_group = [];
    suggestions.Groups = session.web.Widget.extend({
        events: {
            'click .oe_remove_suggested_group': "remove_suggested_group",
            'click .oe_join_group': "join_group",
            'click .oe_open_group': "open_group"
        },
        init: function (parent, action) {
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
                _(res).each(function(result) {
                    result['image']=self.session.url('/web/binary/image', {model: 'mail.group', field: 'image_small', id: result.id});
                });

                self.suggestions = res;
            });
            return $.when(group).done(function() {
                self.$el.html( QWeb.render("mail.suggestions.groups", {'widget': self}) );
                if (self.suggestions.length === 0) {
                    self.$(".oe_sidebar_group").hide();
                }
            });
        },
        open_group:function(event) {
            var self = this;
            var id = JSON.parse($(event.currentTarget).attr("id"));
            action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.group',
                res_id: id,
                views: [[false, 'form']],
                target: 'current'
            };
            this.do_action(action);
        },
        join_group:function(event) {
            var self = this;
            return this.mail_group.call('message_subscribe_users', [[$(event.currentTarget).attr('id')],[this.session.uid]]).then(function(res) {
                self.get_suggested_group();
            });
        },
        remove_suggested_group: function(event) {
            var self = this;
            removed_suggested_group.push($(event.currentTarget).attr('id'));
            self.get_suggested_group();
        }
    });

    mail.Wall.include({
        start: function(options) {
            this._super(options);
            var self = this;
            var sidebar = new suggestions.Sidebar(self);
            sidebar.appendTo(self.$el.find('.oe_mail_wall_aside'));

            var sug_groups = new suggestions.Groups(self);
            // sug_groups.replace(self.$el.find('.oe_suggestions_groups'));
            $.when(sug_groups.start()).done(function() {
                //self.$el.find('.oe_suggestions_groups').html(sug_groups.$el.html());
                sug_groups.replace( self.$el.find('.oe_suggestions_groups') );
            });

        }
    });

};
