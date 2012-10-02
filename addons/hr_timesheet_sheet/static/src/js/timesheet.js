
openerp.hr_timesheet_sheet = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_timesheet_sheet.WeeklyTimesheet = instance.web.form.FormWidget.extend(instance.web.form.ReinitializeWidgetMixin, {
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
            this.field_manager.on("field_changed:user_id", this, function() {
                this.set({"user_id": this.field_manager.get_field_value("user_id")});
            });
            this.on("change:sheets", this, this.update_sheets);
            this.res_o2m_drop = new instance.web.DropMisordered();
            this.render_drop = new instance.web.DropMisordered();
            this.description_line = _t("/");
        },
        query_sheets: function() {
            var self = this;
            if (self.updating)
                return;
            var commands = this.field_manager.get_field_value("timesheet_ids");
            this.res_o2m_drop.add(new instance.web.Model(this.view.model).call("resolve_2many_commands", ["timesheet_ids", commands, [], 
                    new instance.web.CompoundContext()]))
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
        initialize_field: function() {
            instance.web.form.ReinitializeWidgetMixin.initialize_field.call(this);
            var self = this;
            self.on("change:sheets", self, self.initialize_content);
            self.on("change:date_to", self, self.initialize_content);
            self.on("change:date_from", self, self.initialize_content);
            self.on("change:user_id", self, self.initialize_content);
        },
        initialize_content: function() {
            var self = this;
            if (self.setting)
                return;
            // don't render anything until we have date_to and date_from
            if (!self.get("date_to") || !self.get("date_from"))
                return;

            // it's important to use those vars to avoid race conditions
            var dates;
            var accounts;
            var account_names;
            var default_get;
            return this.render_drop.add(new instance.web.Model("hr.analytic.timesheet").call("default_get", [
                ['account_id','general_account_id', 'journal_id','date','name','user_id','product_id','product_uom_id','to_invoice','amount','unit_amount'],
                new instance.web.CompoundContext({'user_id': self.get('user_id')})]).pipe(function(result) {
                default_get = result;
                // calculating dates
                dates = [];
                var start = self.get("date_from");
                var end = self.get("date_to");
                while (start <= end) {
                    dates.push(start);
                    start = start.clone().addDays(1);
                }
                // group by account
                accounts = _(self.get("sheets")).chain()
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
                    var days = _.map(dates, function(date) {
                        var day = {day: date, lines: index[instance.web.date_to_str(date)] || []};
                        // add line where we will insert/remove hours
                        var to_add = _.find(day.lines, function(line) { return line.name === self.description_line });
                        if (to_add) {
                            day.lines = _.without(day.lines, to_add);
                            day.lines.unshift(to_add);
                        } else {
                            day.lines.unshift(_.extend(_.clone(default_get), {
                                name: self.description_line,
                                unit_amount: 0,
                                date: instance.web.date_to_str(date),
                                account_id: account_id,
                            }));
                        }
                        return day;
                    });
                    return {account: account_id, days: days};
                }).sortBy(function(account) {
                    return account.account;
                }).value();

                // we need the name_get of the analytic accounts
                return new instance.web.Model("account.analytic.account").call("name_get", [_.pluck(accounts, "account"),
                    new instance.web.CompoundContext()]).pipe(function(result) {
                    account_names = {};
                    _.each(result, function(el) {
                        account_names[el[0]] = el[1];
                    });
                });;
            })).pipe(function(result) {
                // we put all the gathered data in self, then we render
                self.dates = dates;
                self.accounts = accounts;
                self.account_names = account_names;
                self.default_get = default_get;
                //real rendering
                self.display_data();
            });
        },
        display_data: function() {
            var self = this;
            self.$el.html(QWeb.render("hr_timesheet_sheet.WeeklyTimesheet", {widget: self}));
            _.each(self.accounts, function(account) {
                _.each(_.range(account.days.length), function(day_count) {
                    if (!self.get('effective_readonly')) {
                        self.get_box(account, day_count).val(self.sum_box(account, day_count)).change(function() {
                            var num = Number($(this).val());
                            if (isNaN(num)) {
                                $(this).val(self.sum_box(account, day_count));
                            } else {
                                account.days[day_count].lines[0].unit_amount += num - self.sum_box(account, day_count);
                                self.get_total(account).html(self.sum_total(account));
                                self.get_day_total(day_count).html(self.sum_day_total(day_count));
                                self.get_super_total().html(self.sum_super_total());
                                self.sync();
                            }
                        });
                    } else {
                        self.get_box(account, day_count).html(self.sum_box(account, day_count));
                    }
                });
                self.get_total(account).html(self.sum_total(account));
            });
            _.each(_.range(self.dates.length), function(day_count) {
                self.get_day_total(day_count).html(self.sum_day_total(day_count));
            });
            self.get_super_total().html(self.sum_super_total());
        },
        get_box: function(account, day_count) {
            return this.$('[data-account="' + account.account + '"][data-day-count="' + day_count + '"]');
        },
        get_total: function(account) {
            return this.$('[data-account-total="' + account.account + '"]');
        },
        get_day_total: function(day_count) {
            return this.$('[data-day-total="' + day_count + '"]');
        },
        get_super_total: function() {
            return this.$('.oe_timesheet_weekly_supertotal');
        },
        sum_box: function(account, day_count) {
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
        sum_day_total: function(day_count) {
            var total = 0;
            _.each(this.accounts, function(account) {
                _.each(account.days[day_count].lines, function(line) {
                    total += line.unit_amount;
                });
            });
            return total;
        },
        sum_super_total: function(account) {
            var self = this;
            var total = 0;
            _.each(self.accounts, function(account) {
                total += self.sum_total(account);
            });
            return total;
        },
        sync: function() {
            var self = this;
            var ops = [];
            var auth_keys = _.extend(_.clone(self.default_get), {
                name: true, unit_amount: true, date: true, account_id:true,
            });

            _.each(self.accounts, function(account) {
                _.each(account.days, function(day) {
                    _.each(day.lines, function(line) {
                        if (line.unit_amount !== 0) {
                            var tmp = _.clone(line);
                            tmp.id = undefined;
                            _.each(line, function(v, k) {
                                if (v instanceof Array) {
                                    tmp[k] = v[0];
                                }
                            });
                            // we have to remove some keys, because analytic lines are shitty
                            _.each(_.keys(tmp), function(key) {
                                if (auth_keys[key] === undefined) {
                                    tmp[key] = undefined;
                                }
                            });
                            ops.push(tmp);
                        }
                    });
                });
            });
            self.setting = true;
            self.set({sheets: ops});
            self.setting = false;
        },
    });

    instance.web.form.custom_widgets.add('weekly_timesheet', 'instance.hr_timesheet_sheet.WeeklyTimesheet');

};
