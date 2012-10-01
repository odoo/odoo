
openerp.hr_timesheet_sheet = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_timesheet_sheet.WeeklyTimesheet = instance.web.form.FormWidget.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.set({
                sheets: [],
                date_to: false,
                date_from: false,
            });
            this.field_manager.on("field_changed:timesheet_ids", this, this.query_sheets);
            this.field_manager.on("field_changed:date_from", this, function() {
                this.set({"date_from": instance.web.str_to_date(this.field_manager.get_field_value("date_from"))});
            });
            this.field_manager.on("field_changed:date_to", this, function() {
                this.set({"date_to": instance.web.str_to_date(this.field_manager.get_field_value("date_to"))});
            });
            this.on("change:sheets", this, this.update_sheets);
            this.res_o2m_drop = new instance.web.DropMisordered();
            this.render_drop = new instance.web.DropMisordered();
            this.description_line = _t("No description");
        },
        query_sheets: function() {
            var self = this;
            if (self.updating)
                return;
            var commands = this.field_manager.get_field_value("timesheet_ids");
            this.res_o2m_drop.add(new instance.web.Model(this.view.model).call("resolve_2many_commands", ["timesheet_ids", commands, []]))
                .then(function(result) {
                self.querying = true;
                self.set({sheets: result});
                self.querying = false;
            });
        },
        update_sheets: function() {
            var self = this;
            if (self.querying)
                return;
            self.updating = true;
            self.field_manager.set_values({timesheet_ids: self.get("sheets")}).then(function() {
                self.updating = false;
            });
        },
        start: function() {
            this.on("change:sheets", this, this.render);
            this.on("change:date_to", this, this.render);
            this.on("change:date_from", this, this.render);
            this.render();
        },
        render: function() {
            var self = this;
            if (self.setting)
                return;
            // don't render anything until we have date_to and date_from
            if (!self.get("date_to") || !self.get("date_from"))
                return;
            // calculating dates
            self.dates = [];
            var start = self.get("date_from");
            var end = self.get("date_to");
            while (start <= end) {
                self.dates.push(start);
                start = start.clone().addDays(1);
            }
            // group by account
            self.accounts = _(this.get("sheets")).chain()
            .map(function(el) {
                // much simpler to use only the id in all cases
                if (typeof(el.account_id) === "object")
                    el.account_id = el.account_id[0];
                return el;
            })
            .groupBy("account_id")
            .map(function(lines, account_id) {
                // group by days
                account_id = account_id === "false" ? false :  Number(account_id);
                var index = _.groupBy(lines, "date");
                var days = _.map(self.dates, function(date) {
                    var day = {day: date, lines: index[instance.web.date_to_str(date)] || []};
                    // add line where we will insert/remove hours
                    var to_add = _.find(day.lines, function(line) { return line.name === self.description_line });
                    if (to_add) {
                        day.lines = _.without(to_add);
                        day.lines.unshift(to_add);
                    } else {
                        day.lines.unshift({
                            name: self.description_line,
                            unit_amount: 0,
                            date: instance.web.date_to_str(date),
                            account_id: account_id,
                        });
                    }
                    return day;
                });
                return {account: account_id, days: days};
            }).sortBy(function(account) {
                return account.account;
            }).value();

            // we need the name_get of the analytic accounts
            this.render_drop.add(new instance.web.Model("account.analytic.account").call("name_get", [_.pluck(self.accounts, "account")]))
                .pipe(function(result) {
                self.account_names = {};
                _.each(result, function(el) {
                    self.account_names[el[0]] = el[1];
                });
                //real rendering
                self.display_data();
            });
        },
        display_data: function() {
            var self = this;
            self.$el.html(QWeb.render("hr_timesheet_sheet.WeeklyTimesheet", {widget: self}));
            _.each(self.accounts, function(account) {
                _.each(_.range(account.days.length), function(day_count) {
                    self.get_case(account, day_count).val(self.sum_case(account, day_count)).change(function() {
                        var num = Number($(this).val());
                        if (isNaN(num)) {
                            $(this).val(self.sum_case(account, day_count));
                        } else {
                            account.days[day_count].lines[0].unit_amount += num - self.sum_case(account, day_count);
                            self.get_total(account).html(self.sum_total(account));
                        }
                    });
                });
                self.get_total(account).html(self.sum_total(account));
            });
        },
        get_case: function(account, day_count) {
            return this.$('[data-account="' + account.account + '"][data-day-count="' + day_count + '"]');
        },
        get_total: function(account) {
            return this.$('[data-account-total="' + account.account + '"]');
        },
        sum_case: function(account, day_count) {
            var line_total = 0;
            _.each(account.days[day_count].lines, function(line) {
                line_total += line.unit_amount;
            });
            return line_total;
        },
        sum_total: function(account) {
            var total = 0;
            _.each(account.days, function(day) {
                _.each(day.lines, function(line) {
                    total += line.unit_amount;
                });
            });
            return total;
        },
    });

    instance.web.form.custom_widgets.add('weekly_timesheet', 'instance.hr_timesheet_sheet.WeeklyTimesheet');

};
