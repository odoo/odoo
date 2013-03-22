openerp.gamification = function(instance) {
    console.log("Debug statement: file loaded");

    instance.Side_bar = instance.mail.Widget.include( {
        init: function (parent, action) {
            console.log("Init function");
            var self = this;
            this._super(parent, action);
            this.deferred = $.Deferred();
            this.res_user = new instance.web.DataSetSearch(this, 'res.users');
            this.goals_info = {};
            console.log("init");
        },
        renderElement: function() {
            var self = this;
            this._super.apply(this, arguments);
            console.log("Render!");
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
    });
};
