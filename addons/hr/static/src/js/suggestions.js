openerp.hr = function(session) {
    var _t = session.web._t;
    var QWeb = session.web.qweb;

    var suggestions = session.suggestions;
    var removed_suggested_employee = session.removed_suggested_employee = [];
    suggestions.Employees = session.mail.Wall.include({
        events: {
            'click .oe_remove_suggested_employee': "remove_suggested_employee",
            'click .oe_follow_employee': "follow_employee",
            'click .oe_open_employee': "open_employee"
        },
        init: function (parent, action) {
            var self = this;
            this._super(parent, action);
            this.deferred = $.Deferred();
            this.hr_employee = new session.web.DataSetSearch(this, 'hr.employee');
            this.suggestions = [];
        },
        start: function() {
            var tmp = this._super.apply(this, arguments);
            var self = this;

            var res = self.get_suggested_employee();
            $.when(res).done(function() {});
            return tmp;
        },
        get_suggested_employee: function () {
            var self = this;
            var employee = self.hr_employee.call('get_suggested_thread', {'removed_suggested_threads':removed_suggested_employee}).then(function(res) {
                _(res).each(function(result) {
                    result['image']=self.session.url('/web/binary/image', {model: 'hr.employee', field: 'image_small', id: result.id});
                });
                self.suggestions = res;
            });
            return $.when(employee).done(function() {
                self.$el.find('.oe_suggestions_employees').html( QWeb.render("hr.suggestions.employee", {'widget': self}) );
                if (self.suggestions.length === 0) {
                    self.$(".oe_sidebar_employee").hide();
                } else {
                    // self.renderFollowButtons();
                }
            });
        },
        renderFollowButtons: function() {
            var self = this;
            self.dfm = new session.web.form.DefaultFieldManager(self);
            // Generate a FieldMonetary for each .oe_goal_field_monetary
            self.$el.find(".oe_follow_employee").each(function() {
                follower_field = new session.mail_followers.Followers(self.dfm, {
                    attrs: {
                        view: self.view
                    }
                });
                follower_field.set('value', parseInt($(this).text(), 10));
                // follower_field.replace($(this));
            });
        },
        open_employee:function(event) {
            var self = this;
            var id = JSON.parse($(event.currentTarget).attr("id"));
            action = {
                type: 'ir.actions.act_window',
                res_model: 'hr.employee',
                res_id: id,
                views: [[false, 'form']],
                target: 'current'
            };
            this.do_action(action);
        },
        follow_employee:function(event) {
            var self = this;
            employee_id = parseInt($(event.currentTarget).attr('id'), 10);
            return this.hr_employee.call('message_subscribe_users', [[employee_id], [this.session.uid], undefined]).then(function(res) {
                self.get_suggested_employee();
            });
        },
        remove_suggested_employee: function(event) {
            var self = this;
            removed_suggested_employee.push($(event.currentTarget).attr('id'));
            self.get_suggested_employee();
        }
    });

};
