openerp.gamification = function(instance) {
    console.log("Debug statement: file loaded");
    var QWeb = instance.web.qweb;

    instance.gamification.Sidebar = instance.web.Widget.extend({
        template: 'gamification.user_wall_sidebar',
        init: function (parent, action) {
            var self = this;
            this._super(parent, action);
            this.deferred = $.Deferred();
            this.res_user = new instance.web.DataSetSearch(this, 'res.users');
            this.goals_info = {};
        },
        events: {
            'click a.oe_update_goal': function(event) {
                var self = this;
                var goal_id = parseInt(event.currentTarget.id);
                var goal_updated = new instance.web.Model('gamification.goal').call('update', [[goal_id]]);
                $.when(goal_updated).done(function() {
                    self.get_goal_todo_info();
                });
            },
            'click a.oe_show_description': function(event) {
                var goal_id = parseInt(event.currentTarget.id);
                this.$el.find('.oe_type_description_'+goal_id).toggle(10);
            },
            'click a.oe_goal_action': function(event) {
                var self = this;
                var goal_id = parseInt(event.currentTarget.id);
                var goal_action = new instance.web.Model('gamification.goal').call('get_action', [goal_id]).then(function(res) {
                    goal_action['action'] = res;
                });
                $.when(goal_action).done(function() {
                    console.log(goal_action);
                    var action_manager = new instance.web.ActionManager(this);
                    action_manager.do_action(goal_action.action);

                    //var form = action_manager.dialog_widget.views.form.controller;
                });

            }
        },
        renderElement: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.get_goal_todo_info();
        },
        render_template: function(target,template) {
            var self = this;
            target.append(QWeb.render(template,{'widget': self}));
        },
        render_template_replace: function(target,template) {
            var self = this;
            target.html(QWeb.render(template,{'widget': self}));
        },
        get_goal_todo_info: function() {
            var self = this;
            var goals_info = this.res_user.call('get_goals_todo_info', {}).then(function(res) {
                self.goals_info['info'] = res
            });
            $.when(goals_info).done(function() {
                console.log(self.goals_info.info);
                if(self.goals_info.info.length > 0){
                    self.render_template_replace(self.$el.filter(".oe_gamification_goal"),'gamification.goal_list_to_do');
                    self.$el.find('.oe_type_description').hide();
                }
            });
        },
    });

    instance.mail.Widget.include({
        init: function (parent, action) {
            var self = this;
            this._super(parent, action);
        },
        start: function() {
            this._super();
            var self = this;
            var sidebar = new instance.gamification.Sidebar(self);
            sidebar.appendTo($('.oe_mail_wall_aside'));
        }
    });
};
