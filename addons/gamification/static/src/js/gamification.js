odoo.define('gamification.gamification', function(require) {
"use strict";

var mail = require('mail.mail');
var core = require('web.core');
var form_common = require('web.form_common');
var Model = require('web.DataModel');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var Sidebar = Widget.extend({
    template: 'gamification.UserWallSidebar',
    init: function (parent, action) {
        this._super(parent, action);
        this.deferred = $.Deferred();
        this.goals_info = {};
        this.challenge_suggestions = {};
        $(document).off('keydown.klistener');
    },
    events: {
        // update a challenge and related goals
        'click i.oe_update_challenge': function(event) {
            var self = this;
            var challenge_id = parseInt(event.currentTarget.id, 10);
            var goals_updated = new Model('gamification.challenge').call('quick_update', [challenge_id]);
            $.when(goals_updated).done(function() {
                self.get_goal_todo_info();
            });
        },
        // action to modify a goal
        'click a.oe_goal_action': function(event) {
            var self = this;
            var goal_id = parseInt(event.currentTarget.id, 10);
            var goal_action = new Model('gamification.goal').call('get_action', [goal_id]).then(function(res) {
                goal_action.action = res;
            });
            $.when(goal_action).done(function() {
                var action = self.do_action(goal_action.action);
                $.when(action).done(function () {
                    new Model('gamification.goal').call('update', [[goal_id]]).then(function(res) {
                        self.get_goal_todo_info();
                    });
                });
            });
        },
        // get more info about a challenge request
        'click a.oe_challenge_reply': function(event) {
            var self = this;
            var challenge_id = parseInt(event.currentTarget.id, 10);
            var challenge_action = new Model('gamification.challenge').call('reply_challenge_wizard', [challenge_id]).then(function(res) {
                challenge_action.action = res;
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
        var challenges = new Model('res.users').call('get_serialised_gamification_summary', []).then(function(result) {
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
        var challenge_suggestions = new Model('res.users').call('get_challenge_suggestions', []).then(function(result) {
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
        var FieldMonetary = core.form_widget_registry.get('monetary');
        self.dfm = new form_common.DefaultFieldManager(self);
        // Generate a FieldMonetary for each .oe_goal_field_monetary
        item.find(".oe_goal_field_monetary").each(function() {
            var currency_id = parseInt( $(this).attr('data-id'), 10);
            var money_field = new FieldMonetary(self.dfm, {
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
        item.find(".oe_user_avatar").each(function() {
            var user_id = parseInt( $(this).attr('data-id'), 10);
            var url = session.url('/web/image', {model: 'res.users', field: 'image_small', id: user_id});
            $(this).attr("src", url);
        });
    }
});

});
