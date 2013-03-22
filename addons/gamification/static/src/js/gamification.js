openerp.gamification = function(instance) {
    console.log("Debug statement: file loaded");

    instance.Side_bar = instance.mail.Widget.include( {
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
                var goal_id = parseInt(event.target.id);
                console.log(goal_id);
                var goal_updated = new instance.web.Model('gamification.goal').call('update', [[goal_id]]);
                $.when(goal_updated).done(function() {
                    self.get_goal_todo_info();
                });
            }
        },
        renderElement: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.render_template(self.$el.filter(".oe_user_sidebar"),'user_wall');
            self.get_goal_todo_info();
        },
        render_template: function(target,template) {
            var self = this;
            target.append(instance.web.qweb.render(template,{'widget': self}));
        },
        render_template_replace: function(target,template) {
            var self = this;
            target.html(instance.web.qweb.render(template,{'widget': self}));
        },
        get_goal_todo_info: function() {
            var self = this;
            console.log(this);
            var goals_info = this.res_user.call('get_goals_todo_info', {}).then(function(res) {
                self.goals_info['info'] = res
            });
            $.when(goals_info).done(function() {
                console.log(self.goals_info.info);
                if(self.goals_info.info.length > 0){
                    self.render_template_replace(self.$el.find(".oe_gamification_goal"),'goal_list_to_do');
                }
            });
        },
        update_goal: function() {
            console.log(this);
            console.log(instance.Side_bar);
            var goal_update = new instance.web.Model('gamification.goal').call('update', [[parseInt(this.id)]]);
            $.when(goal_update).done(function() {
                // $(".oe_user_sidebar").find(".oe_gamification_goal").html(instance.web.qweb.render('goal_list_to_do'));
            });
        },
    });
};
