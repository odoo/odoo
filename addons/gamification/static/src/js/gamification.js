openerp.gamification = function(instance) {
    var QWeb = instance.web.qweb;

    instance.gamification.Sidebar = instance.web.Widget.extend({
        template: 'gamification.UserWallSidebar',
        init: function (parent, action) {
            var self = this;
            this._super(parent, action);
            this.deferred = $.Deferred();
            this.goals_info = {};
            this.challenge_suggestions = {};
            $(document).off('keydown.klistener');
        },
        events: {
            // update a challenge and related goals
            'click a.oe_update_challenge': function(event) {
                var self = this;
                var challenge_id = parseInt(event.currentTarget.id, 10);
                var goals_updated = new instance.web.Model('gamification.challenge').call('quick_update', [challenge_id]);
                $.when(goals_updated).done(function() {
                    self.get_goal_todo_info();
                });
            },
            // action to modify a goal
            'click a.oe_goal_action': function(event) {
                var self = this;
                var goal_id = parseInt(event.currentTarget.id, 10);
                var goal_action = new instance.web.Model('gamification.goal').call('get_action', [goal_id]).then(function(res) {
                    goal_action['action'] = res;
                });
                $.when(goal_action).done(function() {
                    var action = self.do_action(goal_action.action);
                    $.when(action).done(function () {
                        new instance.web.Model('gamification.goal').call('update', [[goal_id]]).then(function(res) {
                            self.get_goal_todo_info();
                        });
                    });
                });
            },
            // get more info about a challenge request
            'click a.oe_challenge_reply': function(event) {
                var self = this;
                var challenge_id = parseInt(event.currentTarget.id, 10);
                var challenge_action = new instance.web.Model('gamification.challenge').call('reply_challenge_wizard', [challenge_id]).then(function(res) {
                    challenge_action['action'] = res;
                });
                $.when(challenge_action).done(function() {
                    self.do_action(challenge_action.action).done(function () {
                        self.get_goal_todo_info();
                    });
                });
            }
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.get_goal_todo_info();
            self.get_challenge_suggestions();
        },
        get_goal_todo_info: function() {
            var self = this;
            var challenges = new instance.web.Model('res.users').call('get_serialised_gamification_summary', []).then(function(result) {
                if (result.length === 0) {
                    self.$el.find(".oe_gamification_challenge_list").hide();
                } else {
                    self.$el.find(".oe_gamification_challenge_list").empty();
                    _.each(result, function(item){
                        var $item = $(QWeb.render("gamification.ChallengeSummary", {challenge: item}));
                        self.render_money_fields($item);
                        self.render_user_avatars($item);
                        self.$el.find('.oe_gamification_challenge_list').append($item);
                    });
                }
            });
        },
        get_challenge_suggestions: function() {
            var self = this;
            var challenge_suggestions = new instance.web.Model('res.users').call('get_challenge_suggestions', []).then(function(result) {
                if (result.length === 0) {
                    self.$el.find(".oe_gamification_suggestion").hide();
                } else {
                    var $item = $(QWeb.render("gamification.ChallengeSuggestion", {challenges: result}));
                    self.$el.find('.oe_gamification_suggestion').append($item);
                }
            });
        },
        render_money_fields: function(item) {
            var self = this;
            self.dfm = new instance.web.form.DefaultFieldManager(self);
            // Generate a FieldMonetary for each .oe_goal_field_monetary
            item.find(".oe_goal_field_monetary").each(function() {
                var currency_id = parseInt( $(this).attr('data-id'), 10);
                money_field = new instance.web.form.FieldMonetary(self.dfm, {
                    attrs: {
                        modifiers: '{"readonly": true}'
                    }
                });
                money_field.set('currency', currency_id);
                money_field.get_currency_info();
                money_field.set('value', parseInt($(this).text(), 10));
                money_field.replace($(this));
            });
        },
        render_user_avatars: function(item) {
            var self = this;
            item.find(".oe_user_avatar").each(function() {
                var user_id = parseInt( $(this).attr('data-id'), 10);
                var url = instance.session.url('/web/binary/image', {model: 'res.users', field: 'image_small', id: user_id});
                $(this).attr("src", url);
            });
        }
    });

    instance.web.WebClient.include({
        to_kitten: function() {
            this._super();
            new instance.web.Model('gamification.badge').call('check_progress', []);
        }
    });

    instance.mail.Wall.include({
        start: function() {
            this._super();
            var sidebar = new instance.gamification.Sidebar(this);
            sidebar.appendTo($('.oe_mail_wall_aside'));
        },
    });
    
};
