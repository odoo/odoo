
openerp.hr_timesheet_sheet = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_timesheet_sheet.WeeklyTimesheet = instance.web.form.FormWidget.extend(instance.web.form.ReinitializeWidgetMixin, {
        events: {
            "click .oe_timesheet_weekly_account a": "go_to",
        },
        init: function() {
            this._super.apply(this, arguments);
            this.set({
                sheets: [],
                date_to: false,
                date_from: false,
            });
            this.updating = false;
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
        go_to: function(event) {
            var id = JSON.parse($(event.target).data("id"));
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: "account.analytic.account",
                res_id: id,
                views: [[false, 'form']],
                target: 'current'
            });
        },
        query_sheets: function() {
            var self = this;
            if (self.updating)
                return;
            var commands = this.field_manager.get_field_value("timesheet_ids");
            this.res_o2m_drop.add(new instance.web.Model(this.view.model).call("resolve_2many_commands", ["timesheet_ids", commands, [], 
                    new instance.web.CompoundContext()]))
                .done(function(result) {
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
            self.field_manager.set_values({timesheet_ids: self.get("sheets")}).done(function() {
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
            this.destroy_content();

            // it's important to use those vars to avoid race conditions
            var dates;
            var accounts;
            var account_names;
            var default_get;
            return this.render_drop.add(new instance.web.Model("hr.analytic.timesheet").call("default_get", [
                ['account_id','general_account_id', 'journal_id','date','name','user_id','product_id','product_uom_id','to_invoice','amount','unit_amount'],
                new instance.web.CompoundContext({'user_id': self.get('user_id')})]).then(function(result) {
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
                .groupBy("account_id").value();

                var account_ids = _.map(_.keys(accounts), function(el) { return el === "false" ? false : Number(el) });

                return new instance.web.Model("hr.analytic.timesheet").call("multi_on_change_account_id", [[], account_ids,
                    new instance.web.CompoundContext({'user_id': self.get('user_id')})]).then(function(accounts_defaults) {
                    accounts = _(accounts).chain().map(function(lines, account_id) {
                        account_defaults = _.extend({}, default_get, (accounts_defaults[account_id] || {}).value || {});
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
                                day.lines.unshift(_.extend(_.clone(account_defaults), {
                                    name: self.description_line,
                                    unit_amount: 0,
                                    date: instance.web.date_to_str(date),
                                    account_id: account_id,
                                }));
                            }
                            return day;
                        });
                        return {account: account_id, days: days, account_defaults: account_defaults};
                    }).value();

                    // we need the name_get of the analytic accounts
                    return new instance.web.Model("account.analytic.account").call("name_get", [_.pluck(accounts, "account"),
                        new instance.web.CompoundContext()]).then(function(result) {
                        account_names = {};
                        _.each(result, function(el) {
                            account_names[el[0]] = el[1];
                        });
                        accounts = _.sortBy(accounts, function(el) {
                            return account_names[el.account];
                        });
                    });;
                });
            })).then(function(result) {
                // we put all the gathered data in self, then we render
                self.dates = dates;
                self.accounts = accounts;
                self.account_names = account_names;
                self.default_get = default_get;
                //real rendering
                self.display_data();
            });
        },
        destroy_content: function() {
            if (this.dfm) {
                this.dfm.destroy();
                this.dfm = undefined;
            }
        },
        is_valid_value:function(value){
            var split_value = value.split(":");
            var valid_value = true;
            if (split_value.length > 2)return false;
            _.detect(split_value,function(num){
                if(isNaN(num)){
                    valid_value = false;
                }
            })
            return valid_value;
        },
        display_data: function() {
            var self = this;
            self.$el.html(QWeb.render("hr_timesheet_sheet.WeeklyTimesheet", {widget: self}));
            _.each(self.accounts, function(account) {
                _.each(_.range(account.days.length), function(day_count) {
                    if (!self.get('effective_readonly')) {
                        self.get_box(account, day_count).val(self.sum_box(account, day_count, true)).change(function() {
                            var num = $(this).val();
                            if (self.is_valid_value(num)){
                                num = Number(self.parse_client(num));
                            } 
                            if (isNaN(num)) {
                                $(this).val(self.sum_box(account, day_count, true));
                            } else {
                                account.days[day_count].lines[0].unit_amount += num - self.sum_box(account, day_count);
                                self.display_totals();
                                self.sync();
                                 if(!isNaN($(this).val())){
                                    $(this).val(self.sum_box(account, day_count, true));
                                }
                            }
                        });
                    } else {
                        self.get_box(account, day_count).html(self.sum_box(account, day_count, true));
                    }
                });
            });
            self.display_totals();
            self.$(".oe_timesheet_weekly_adding button").click(_.bind(this.init_add_account, this));
        },
        init_add_account: function() {
            var self = this;
            if (self.dfm)
                return;
            self.$(".oe_timesheet_weekly_add_row").show();
            self.dfm = new instance.web.form.DefaultFieldManager(self);
            self.dfm.extend_field_desc({
                account: {
                    relation: "account.analytic.account",
                },
            });
            self.account_m2o = new instance.web.form.FieldMany2One(self.dfm, {
                attrs: {
                    name: "account",
                    type: "many2one",
                    domain: [
                        ['type','in',['normal', 'contract']],
                        ['state', '<>', 'close'],
                        ['use_timesheets','=',1],
                        ['id', 'not in', _.pluck(self.accounts, "account")],
                    ],
                    context: {
                        default_use_timesheets: 1,
                        default_type: "contract",
                    },
                    modifiers: '{"required": true}',
                },
            });
            self.account_m2o.prependTo(self.$(".oe_timesheet_weekly_add_row td"));
            self.$(".oe_timesheet_weekly_add_row button").click(function() {
                var id = self.account_m2o.get_value();
                if (id === false) {
                    self.dfm.set({display_invalid_fields: true});
                    return;
                }
                var ops = self.generate_o2m_value();
                new instance.web.Model("hr.analytic.timesheet").call("on_change_account_id", [[], id]).then(function(res) {
                    var def = _.extend({}, self.default_get, res.value, {
                        name: self.description_line,
                        unit_amount: 0,
                        date: instance.web.date_to_str(self.dates[0]),
                        account_id: id,
                    });
                    ops.push(def);
                    self.set({"sheets": ops});
                });
            });
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
        sum_box: function(account, day_count, show_value_in_hour) {
            var line_total = 0;
            _.each(account.days[day_count].lines, function(line) {
                line_total += line.unit_amount;
            });
            return (show_value_in_hour)?this.format_client(line_total):line_total;
        },
        display_totals: function() {
            var self = this;
            var day_tots = _.map(_.range(self.dates.length), function() { return 0 });
            var super_tot = 0;
            _.each(self.accounts, function(account) {
                var acc_tot = 0;
                _.each(_.range(self.dates.length), function(day_count) {
                    var sum = self.sum_box(account, day_count);
                    acc_tot += sum;
                    day_tots[day_count] += sum;
                    super_tot += sum;
                });
                self.get_total(account).html(self.format_client(acc_tot));
            });
            _.each(_.range(self.dates.length), function(day_count) {
                self.get_day_total(day_count).html(self.format_client(day_tots[day_count]));
            });
            self.get_super_total().html(self.format_client(super_tot));
        },
        sync: function() {
            var self = this;
            self.setting = true;
            self.set({sheets: this.generate_o2m_value()});
            self.setting = false;
        },
        //converts hour value to float
        parse_client: function(value) {
            return instance.web.parse_value(value, { type:"float_time" });
        },
        //converts float value to hour
        format_client:function(value){
            return instance.web.format_value(value, { type:"float_time" });
        },
        generate_o2m_value: function() {
            var self = this;
            var ops = [];

            _.each(self.accounts, function(account) {
                var auth_keys = _.extend(_.clone(account.account_defaults), {
                    name: true, unit_amount: true, date: true, account_id:true,
                });
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
            return ops;
        },
    });

    instance.web.form.custom_widgets.add('weekly_timesheet', 'instance.hr_timesheet_sheet.WeeklyTimesheet');

};
