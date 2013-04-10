openerp.gamification = function(instance) {
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
                var goal_id = parseInt(event.currentTarget.id, 10);
                var goal_updated = new instance.web.Model('gamification.goal').call('update', [[goal_id]]);
                $.when(goal_updated).done(function() {
                    self.get_goal_todo_info();
                });
            },
            'click a.oe_update_plan': function(event) {
                var self = this;
                var plan_id = parseInt(event.currentTarget.id, 10);
                var goals_updated = new instance.web.Model('gamification.goal.plan').call('quick_update', [plan_id]);
                $.when(goals_updated).done(function() {
                    self.get_goal_todo_info();
                });
            },
            'click a.oe_goal_action': function(event) {
                var self = this;
                var goal_id = parseInt(event.currentTarget.id, 10);
                var goal_action = new instance.web.Model('gamification.goal').call('get_action', [goal_id]).then(function(res) {
                    goal_action['action'] = res;
                });
                $.when(goal_action).done(function() {
                    var action_manager = new instance.web.ActionManager(this);
                    action_manager.do_action(goal_action.action).done(function () {
                        self.get_goal_todo_info();
                    });
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
                self.goals_info['info'] = res;
            });
            $.when(goals_info).done(function() {
                if(self.goals_info.info.length > 0){
                    self.render_template_replace(self.$el.filter(".oe_gamification_goal"),'gamification.goal_list_to_do');
                    self.render_money_fields(self.goals_info.info[0].currency);
                    self.render_progress_bars();
                }
            });
        },
        render_money_fields: function(currency_id) {
            var self = this;

            self.dfm = new instance.web.form.DefaultFieldManager(self);
            // Generate a FieldMonetary for each .oe_goal_field_monetary
            self.$el.find(".oe_goal_field_monetary").each(function() {
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
        render_progress_bars: function() {
            var self = this;

            dfm = new instance.web.form.DefaultFieldManager(self);
            // Generate a FieldMonetary for each .oe_goal_field_monetary
            self.$el.find(".oe_goal_progress").each(function() {
                progress_field = new instance.web.form.FieldProgressBar(dfm, {
                    attrs: {
                        modifiers: '{"readonly": true}'
                    }
                });
                progress_field.set('value', $(this).attr('value'));
                progress_field.replace($(this));
            });
        }
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

    instance.web_kanban.KanbanRecord.include({
        start: function () {
            var rendering = this._super();
            var self = this;

            $.when(rendering).done(function() {
                if (self.view.dataset.model === 'gamification.goal' && self.$el.find('.oe_goal_gauge').length == 1) {
                    var unique_id = _.uniqueId("goal_gauge_");
                    self.$el.find('.oe_goal_gauge').attr('id', unique_id);
                    console.log(self.record);
                    var g = new JustGage({
                        id: unique_id,
                        node: self.$el.find('.oe_goal_gauge').empty().get(0),
                        value: self.record.current.raw_value,
                        min: 0,
                        max: self.record.target_goal.raw_value,
                        relativeGaugeSize: true,
                        humanFriendly: true,
                        // add space between value and symbol
                        // textRenderer: function(value) {
                        //     symbol = self.record.type_suffix.raw_value;
                        //     humannbr = humanFriendlyNumber(value, 0)
                        //     if ((humannbr + symbol).length > 6) {
                        //         return humannbr;
                        //     } else {
                        //         return humannbr + " " + symbol;
                        //     }
                        // },
                        label: self.record.type_suffix.raw_value,
                        levelColors: [
                            "#f9c802",
                            "#ff0000",
                            "#a9d70b"
                        ],
                    });
                }
            });
        },
        on_card_clicked: function() {
            if (this.view.dataset.model === 'gamification.goal.plan') {
                this.$('.oe_kanban_project_list a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        }
    });
};
