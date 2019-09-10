openerp.mail.suggestions = function(session, mail) {
    var _t = session.web._t;
    var QWeb = session.web.qweb;

    var suggestions = session.suggestions = {};
    var removed_suggested_group = session.suggestions.removed_suggested_group = [];

    suggestions.Groups = session.web.Widget.extend({
        events: {
            'click .oe_suggestion_remove.oe_suggestion_group': 'stop_group_suggestion',
            'click .oe_suggestion_remove_item.oe_suggestion_group': 'remove_group_suggestion',
            'click .oe_suggestion_join': 'join_group',
        },

        init: function () {
            this._super.apply(this, arguments);
            this.mail_group = new session.web.DataSetSearch(this, 'mail.group');
            this.res_users = new session.web.DataSetSearch(this, 'res.users');
            this.groups = [];
        },

        start: function () {
            this._super.apply(this, arguments);
            return this.fetch_suggested_groups();
        },

        fetch_suggested_groups: function () {
            var self = this;
            var group = self.mail_group.call('get_suggested_thread', {'removed_suggested_threads': removed_suggested_group}).then(function (res) {
                _(res).each(function (result) {
                    result['image']=self.session.url('/web/binary/image', {model: 'mail.group', field: 'image_small', id: result.id});
                });
                self.groups = res;
            });
            return $.when(group).then(this.proxy('display_suggested_groups'));
        },

        display_suggested_groups: function () {
            var suggested_groups = this.$('.oe_sidebar_suggestion.oe_suggestion_group');
            if (suggested_groups) {
                suggested_groups.empty();
            }
            if (this.groups.length === 0) {
                return this.$el.empty();
            }
            return this.$el.empty().html(QWeb.render('mail.suggestions.groups', {'widget': this}));
        },

        join_group: function (event) {
            var self = this;
            var group_id = parseInt($(event.currentTarget).attr('id'), 10);
            return this.mail_group.call('message_subscribe_users', [[group_id], [this.session.uid]]).then(function(res) {
                self.fetch_suggested_groups();
            });
        },

        remove_group_suggestion: function (event) {
            removed_suggested_group.push($(event.currentTarget).attr('id'));
            return this.fetch_suggested_groups();
        },

        stop_group_suggestion: function (event) {
            var self = this;
            return this.res_users.call('stop_showing_groups_suggestions', [this.session.uid]).then(function(res) {
                self.$(".oe_sidebar_suggestion.oe_suggestion_group").hide();
            });
        }
    });

    session.mail.WallSidebar.include({
        start: function () {
            this._super.apply(this, arguments);
            var sug_groups = new suggestions.Groups(this);
            return sug_groups.appendTo(this.$('.oe_suggestions_groups'));
        },
    });

};
