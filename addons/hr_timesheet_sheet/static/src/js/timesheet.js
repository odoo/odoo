openerp.hr_timesheet_sheet = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_timesheet_sheet.Timesheet = instance.web.form.FormWidget.extend(instance.web.form.ReinitializeWidgetMixin, {
        template: "hr_timesheet_sheet.Timesheet",
        init: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.set({
                sheets: [],
                date_to: false,
                date_from: false,
            });
            this.account_id = [];
            this.updating = false;
            this.defs = [];
            this.dfms = [];
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
            this.is_sheets = false;
            this.mode = "week";
            // Original save function is overwritten in order to wait all running deferreds to be done before actually applying the save.
            this.view.original_save = _.bind(this.view.save, this.view);
            this.view.save = function(prepend_on_create){
                self.prepend_on_create = prepend_on_create;
                return $.when.apply($, self.defs).then(function(){
                    return self.view.original_save(self.prepend_on_create);
                });
            };
            this.options = {};
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
            var data_to_update = [], tmp = [];
            if (self.querying)
                return;
            self.updating = true;

            data_to_update = _(self.get("sheets")).chain()
            .map(function(record) {
                if (record.id) {
                    tmp = [1, record.id, record];
                    //delete record.id; //It'll be OK even if we do not delete id key, server will manage and will remove MAGIC COLUMNS from vals
                } else {
                    tmp = [0, false, record];
                }
                return tmp;
            }).value();
            self.field_manager.set_values({timesheet_ids: data_to_update}).done(function() {
                self.updating = false;
            });
        },
        unlink_sheets_records: function(initial_o2m_value, ops) {
            var self = this;
            var data_to_update = [], tmp = [];
            if (self.querying)
                return;
            self.updating = true;
            var is_record_available = function(id) {
                return _.find(ops, function(record) { return record.id === id; });
            };
            data_to_update = _(initial_o2m_value).chain()
            .map(function(record) {
                if (record.id && is_record_available(record.id)) {
                    tmp = [1, record.id, record];
                    //delete record.id; //It'll be OK even if we do not delete id key, server will manage and will remove MAGIC COLUMNS from vals
                } else if(!record.id) {
                    tmp = [0, false, record];
                } else if (!is_record_available(record.id)) {
                    tmp = [2, record.id, false];
                }
                return tmp;
            }).value();
            self.field_manager.set_values({timesheet_ids: data_to_update}).done(function() {
                self.updating = false;
                self.query_sheets();
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
            this.donot_destroy_options = true;
            this.destroy_content();
            this.donot_destroy_options = false;
            // it's important to use those vars to avoid race conditions
            var dates;
            var accounts;
            var account_names;
            var default_get;
            var account_defaults;
            //To check whether we have any submitted  timesheet, if yes then show copy/paste lines link
            if (self.get('user_id')) {
                this.render_drop.add(new instance.web.Model("hr_timesheet_sheet.sheet").call("search", [[['user_id','=',self.get('user_id')], ['date_from', '<=', self.field_manager.get_field_value("date_from")]]]).then(function(result) {
                    if (result.length) {
                        self.is_sheets = true;
                    }
                }));
            }
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
                    var m_start = moment(start).add(1,'days');
                    start = m_start.toDate();
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
                var account_ids = _.map(_.keys(accounts), function(el) { return el === "false" ? false : Number(el); });
                return new instance.web.Model("hr.analytic.timesheet").call("multi_on_change_account_id", [[], account_ids,
                    new instance.web.CompoundContext({'user_id': self.get('user_id')})]).then(function(accounts_defaults) {
                    accounts = _(accounts).chain().map(function(lines, account_id) {
                        var week_count = 0;
                        var previous_week = false;
                        account_defaults = _.extend({}, default_get, (accounts_defaults[account_id] || {}).value || {});
                        // group by days
                        account_id = account_id === "false" ? false :  Number(account_id);
                        var group_by_date = _.groupBy(lines, "date");
                        var days = _.map(dates, function(date, index) {
                            var week = moment(date).week();
                            if (week != previous_week) {
                                week_count += 1;
                            }
                            previous_week = week;
                            var day = {day: date, lines: group_by_date[instance.web.date_to_str(date)] || [], week_count: week_count, day_index: index};
                            // add line where we will insert/remove hours
                            var to_add = _.find(day.lines, function(line) { return line.name === self.description_line;});
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
                    });
                });
            })).then(function(result) {
                // we put all the gathered data in self, then we render
                self.dates = dates;
                if(self.dates.length) {
                    _.extend(self.options, {'week_count': 0});
                }
                self.accounts = accounts;
                self.account_names = account_names;
                self.default_get = default_get;
                self.account_defaults = account_defaults;
                //real rendering
                self.display_data(self.options);
            });
        },
        destroy_content: function() {
            if (!this.donot_destroy_options) {
                this.options = {}; //Otherwise when paging next record it will pass old count and old week
            }
            if (this.dfm) {
                this.dfm.destroy();
                this.dfm = undefined;
            }
            if (this.dfms.length) {
                _.each(this.dfms, function(dfm) {
                    dfm.destroy();
                });
            }
        },
        destroy: function () {
            this._super();
            this.active_widget.destroy();
        },
        is_valid_value: function(value){
            var split_value = value.split(":");
            var valid_value = true;
            if (split_value.length > 2)
                return false;
            _.detect(split_value,function(num){
                if(isNaN(num)){
                    valid_value = false;
                }
            });
            return valid_value;
        },
        display_data: function(options) {
            var self = this;
            if (this.mode == "week") {
                this.active_widget = new instance.hr_timesheet_sheet.WeeklyTimesheet(this, options);
                this.active_widget.replace(self.$el.find(".hr_timesheet_container"));
            } else {
                this.active_widget = new instance.hr_timesheet_sheet.DailyTimesheet(this, options);
                this.active_widget.format_data_in_days().then(function() {
                    self.active_widget.replace(self.$el.find(".hr_timesheet_container"));
                });
            }
        },
        init_account: function(account_ids) {
            var dfm = new instance.web.form.DefaultFieldManager(this);
            dfm.extend_field_desc({
                account: {
                    relation: "account.analytic.account",
                },
            });
            this.dfms.push(dfm);
            return new instance.web.form.FieldMany2One(dfm, {
                attrs: {
                    name: "account",
                    type: "many2one",
                    domain: [
                        ['type','in',['normal', 'contract']],
                        ['state', '<>', 'close'],
                        ['invoice_on_timesheets','=',1],
                        ['id', 'not in', account_ids],
                    ],
                    context: {
                        default_invoice_on_timesheets: 1,
                        default_type: "contract",
                    },
                    modifiers: '{"required": true}',
                },
            });
        },
        init_add_account: function(current_date, account_ids) {
            var self = this;
            if (this.dfm)
                return;
            this.new_account_m2o = this.init_account(account_ids);
            this.dfm = this.new_account_m2o.field_manager;
            this.$(".oe_timesheet_add_row").show();
            this.new_account_m2o.prependTo(this.$(".oe_timesheet_add_row"));
            //this.$(".oe_timesheet_add_row a").click(function() {
            //To support add account on oncahnge of many2one
            this.new_account_m2o.on("change:value", this, function() {
                var id = self.new_account_m2o.get_value();
                if (id === false) {
                    self.new_account_m2o.field_manager.set({display_invalid_fields: true});
                    return;
                }
                var ops = self.active_widget.generate_o2m_value();
                new instance.web.Model("hr.analytic.timesheet").call("on_change_account_id", [[], id]).then(function(res) {
                    var def = _.extend({}, self.default_get, res.value, {
                        name: self.description_line,
                        unit_amount: 0,
                        date: current_date,
                        account_id: id,
                    });
                    ops.push(def);
                    self.set({"sheets": ops});
                });
            });
        },
        do_switch_mode: function (event, options) {
            this.destroy_content();
            var $target = $(event.currentTarget);
            this.mode = (options && options.mode) ? options.mode : $target.data("mode");
            this.display_data(options);
        },
        get_box: function(account, day_count) {
            return this.$('.oe_timesheet_box[data-account="' + account + '"][data-day-count="' + day_count + '"]');
        },
        get_account_placeholder: function(account_id) {
            return this.$(".account_m2o_placeholder[data-id='"+account_id+"']");
        },
        sync: function() {
            this.setting = true;
            this.set({sheets: this.active_widget.generate_o2m_value()});
            this.setting = false;
        },
        parse_client: function(value) {
            //converts hour value to float
            return instance.web.parse_value(value, { type:"float_time" });
        },
        format_client:function(value) {
            //converts float value to hour
            return instance.web.format_value(value, { type:"float_time" });
        },
        ignore_fields: function() {
            return ['line_id'];
        },
    });

instance.hr_timesheet_sheet.DailyTimesheet = instance.web.Widget.extend({
    template: "hr_timesheet_sheet.DailyTimesheet",
    events: {
        "click .oe_timesheet_goto a": "go_to",
        "click .oe_timesheet_daily .oe_nav_button": "navigateAll",
        "click .oe_timesheet_switch": "do_switch_mode",
        "click .oe_copy_accounts a": "copy_accounts",
        "click .oe_timer": "timer",
        "click .oe_delete_line": "on_delete_line",
    },
    init: function (parent, options) {
        var self = this;
        this._super(parent);
        this.parent = parent;
        this.options = options || {};
        this.on("change:count", this, function() {
            _.extend(self.options, {'count': self.get('count')});
            self.parent.options = self.options;
        });
        this.on("change:week_count", this, function() {
            _.extend(self.options, {'week_count': this.get('week_count')});
            self.parent.options = self.options;
        });
        this.set('count', (options || {}).count || 0);
        this.set('week_count', (options || {}).week_count || 0);
        this.set('effective_readonly', this.parent.get("effective_readonly"));
    },
    start: function() {
        this.display_data();
    },
    go_to: function(event) {
        this.parent.go_to(event);
    },
    display_data: function() {
        var self = this;
        var count = self.get('count');
        if(self.days && self.days.length)
            self.week_count = self.days[count].week_count;
        if (self.days && self.days.length) {
            var day_count = count;
             _.each(self.days[count].account_group, function(account){
                if (!self.get('effective_readonly')) {
                    var account_id = account[0].account_id;
                    var account_m2o = self.parent.init_account(_.keys(self.days[self.get('count')].account_group));
                    var placeholder_element = self.parent.get_account_placeholder(account_id);
                    account_m2o.replace(placeholder_element);
                    account_m2o.set_value(account_id);
                    account_m2o.current_value = account_m2o.old_value = account_id;
                    account_m2o.on("change:value", this, function() {
                        if (account_m2o.get('value') === false) {
                            account_m2o.field_manager.set({display_invalid_fields: true});
                            return;
                        }
                        account_m2o.old_value = account_m2o.current_value;
                        //New record will set false in the current value and when new record is set old value = new value(i.e. false)
                        if (account_m2o.get('value')) {
                            account_m2o.current_value = account_m2o.get('value');
                            self.on_change_account(account_m2o.old_value, account_m2o.current_value);
                        }
                    });
                    self.parent.get_box(account[0].account_id, day_count).val(self.sum_box(account, true)).change(function() {
                        var num = $(this).val();
                        if(self.parent.is_valid_value(num)){
                                num = (num == 0)?0:Number(self.parent.parse_client(num));
                        }
                        if (isNaN(num)) {
                            $(this).val(self.sum_box(account, true));
                        } else {
                            account[0].unit_amount += num - self.sum_box(account);
                            var product = (account[0].product_id instanceof Array) ? account[0].product_id[0] : account[0].product_id;
                            var journal = (account[0].journal_id instanceof Array) ? account[0].journal_id[0] : account[0].journal_id;
                            self.parent.defs.push(new instance.web.Model("hr.analytic.timesheet").call("on_change_unit_amount", [[], product, account[0].unit_amount, false, false, journal]).then(function(res) {
                                account[0].amount = res.value.amount || 0;
                                self.sync_parent_data(account[0], day_count);
                                self.display_totals();
                                self.parent.sync();
                            }));
                            if(!isNaN($(this).val())){
                                $(this).val(self.sum_box(account, true));
                            }
                        }
                    });
                    self.get_description_box(account[0].account_id, day_count).off('change').on('change', function(e) {
                        account[0].name = $(this).val();
                        self.parent.sync();
                    });
                } else {
                    self.parent.get_box(account[0].account_id, day_count).html(self.sum_box(account, true));
                }
            });
            self.display_totals();
            self.start_interval();
            self.toggle_active(self.get('count'));
            self.$(".oe_timesheet_daily_adding a").click(_.bind(this.parent.init_add_account, this.parent, instance.web.date_to_str(self.days[self.get('count')].day), _.keys(self.days[self.get('count')].account_group)));
        }
    },
    sync_parent_data: function(updated_account, day_count) {
        /*
            Synchronize data with Timesheet widget, note that we having accounts and all that in Timesheet's intialize_content method
            For day mode we are reformatting data the way day mode accepts
            so when we update input boxes of day mode it will not change main account's lines
            This method will synchronize data of accounts of main Timesheet widget 
        */
        _.each(this.parent.accounts, function(account) {
            if (account.account == updated_account.account_id) {
                account.days[day_count].lines[0]['amount'] = updated_account.amount || 0;
                account.days[day_count].lines[0]['unit_amount'] = updated_account.unit_amount || 0;
            }
        });
    },
    format_data_in_days: function() {
        /*
            This method will use the data of Timesheet widget, it will not call all default_get and etc calls to server,
            Instead this method will only reformat the data in the way day mode requires
            return: it returns deferred object
        */
        var self = this;
        var dates;
        var days;
        var new_account_names;
        dates = [];
        var start = this.parent.get("date_from");
        var end = this.parent.get("date_to");
        while (start <= end) {
            dates.push(start);
            var m_start = moment(start).add(1,'days');
            start = m_start.toDate();
        }
        //groupby date
        new_days = _(self.parent.get("sheets")).chain()
        .map(function(line) {
            if (typeof(line.account_id) === "object")
                line.account_id = line.account_id[0];
            return line;
        })
        .groupBy("date").value();
        var new_account_ids = _(new_days).chain()
        .map(function(el) {
            new_accs = _.map(el, function(entry) {
                return entry.account_id === "false" ? false : (typeof(entry.account_id) === "object" ? Number(entry.account_id[0]) : Number(entry.account_id));
            });
            return new_accs;
        })
        .flatten(true)
        .union().value();

        //Need to add week_count logic, because it is quite possible that timesheet may have two weeks with same number,
        //Say for example create timesheet with 1-1 to 31-12, it is quite possible that 1-1 and 31-12 may come in 0th week, which will create issue in week based logic
        var count = 0;
        var previous_week = false;
        days = _.map(dates, function(date, index) {
            var week = moment(date).week();
            if (week != previous_week) {
                count += 1;
            }
            previous_week = week;
            var account_group = _.groupBy(new_days[instance.web.date_to_str(date)], "account_id");
            var day = {day: date, account_defaults: self.parent.account_defaults, account_group: account_group, week_count: count, day_index: index, };
            return day;
        });
        return new instance.web.Model("account.analytic.account").call("name_get", [new_account_ids,
            new instance.web.CompoundContext()]).then(function(result) {
                new_account_names = {};
                _.each(result, function(el) {
                    new_account_names[el[0]] = el[1];
                });
                //Sorting days accounts based on account_id
                days = _.each(days, function(day) {
                    return _.sortBy(day.account_group, function(el) {
                        return new_account_names[el.account_id];
                    });
                });
                self.new_dates = dates;
                self.account_names = new_account_names;
                self.days = days;
                if(self.days.length) {
                    self.week_count = _.first(self.days).week_count;
                }
        });
    },
    do_switch_mode: function(e) {
        if (this.intervalTimer) {
            clearInterval(this.intervalTimer);
        }
        this.parent.do_switch_mode(e);
    },
    set_day_total: function(day_count, total) {
        return this.$el.find('[data-day-total = "' + day_count + '"]').html(this.parent.format_client(total));;
    },
    get_super_total: function() {
        return this.$('.oe_header_total');
    },
    get_description_box: function(account_id, day_count) {
        return this.$('.oe_edit_input[data-account="' + account_id + '"][data-day-count="' + day_count + '"]');
    },
    sum_box: function(account, show_value_in_hour) {
        var line_total = 0;
        _.each(account, function(line){
            line_total += line.unit_amount;
        });
        return (show_value_in_hour && line_total != 0)?this.parent.format_client(line_total):line_total;
    },
    display_totals: function() {
        var self = this;
        var day_tots = _.map(_.range(self.days.length), function() { return 0;});
        var super_tot = 0;
        var acc_tot = 0;
        _.each(self.days, function(days, day_count) {
            _.each(days.account_group,function(account){
                //TODO: Why not separate method for display timer difference
                if(account[0].date_start){
                    var difference = self.get_date_diff(self.get_current_UTCDate(), account[0].date_start).split(":");
                    account[0]["date_diff_hour"] = difference[0];
                    account[0]["date_diff_minute"] = difference[1];
                }
                var sum = self.sum_box(account);
                acc_tot = acc_tot +  sum;
                day_tots[day_count] += sum;
                super_tot += sum;
            });
        });
        _.each(_.range(self.days.length), function(day_count) {
            self.set_day_total(day_count, day_tots[day_count]);
        });
        self.get_super_total().html("Total <br/><small>" + (self.parent.format_client(super_tot)) + "</small>");
    },
    generate_o2m_value: function() {
        var self = this;
        var ops = [];
        var ignored_fields = self.parent.ignore_fields();
        _.each(self.days, function(day) {
            var auth_keys = _.extend(_.clone(day.account_defaults || {}), {
                id: true, name: true, amount:true, unit_amount: true, date: true, account_id:true, date_start: true,
            });
            _.each(day.account_group, function(account) {
                _.each(account,function(line) {
                    var tmp = _.clone(line);
                    //tmp.id = undefined;
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
                    tmp = _.omit(tmp, ignored_fields);
                    ops.push(tmp);
                });
            });
        });
        return ops;
    },
    is_previous_data_exist: function() {
        var data_exist = false;
        var count = this.get('count');
        while (count >= 0) {
            if (!_.isEmpty(this.days[count].account_group)) {
                data_exist = true;
                break;
            } else {
                count -= 1;
            }
        }
        return data_exist;
    },
    get_last_day_data: function(records) {
        if (!records) {
            return;
        }
        var groupby_date = _.groupBy(records, 'date');
        var get_max_date = function(initial_date) {
            _.each(records, function(record) {
                if (moment(record.date).isAfter(initial_date)) {
                    initial_date = moment(record.date);
                }
            });
            return initial_date;
        };
        var max_date = get_max_date(moment(records[0].date));
        return groupby_date[max_date.format("YYYY-MM-DD")] || {};
    },
    copy_accounts: function(e) {
        /*
         * This method first try to search for previous records in existing timesheet, if there is no previous records
         * then it will fetch last saved timesheet, from that it fetches last day and copy all data of last day here
         */
        var self = this;
        var data_to_copy;
        var onchange_result = {};
        var index = this.get('count');
        var def = $.Deferred();
        while (index >= 0) {
            if(_.isEmpty(self.days[index].account_group)) {
                index -= 1;
            } else {
                data_to_copy = JSON.parse(JSON.stringify(this.days[index].account_group));
                break;
            }
        }
        if (!data_to_copy) {
            (new instance.web.Model("hr_timesheet_sheet.sheet").call("search_read", {
               domain: [['user_id','=',self.parent.get('user_id')], ['date_from', '<=', self.parent.field_manager.get_field_value("date_from")]],
               fields: ['timesheet_ids'],
               order: "date_from DESC",
               limit: 1
            })).then(function(result) {
               if (result.length && result[0].timesheet_ids) {
                   (new instance.web.Model('hr.analytic.timesheet').call('read', {
                       ids: result[0].timesheet_ids,
                       fields: ['name', 'amount', 'unit_amount', 'date', 'account_id', 'date_start', 'general_account_id', 'journal_id', 'user_id', 'product_id', 'product_uom_id', 'to_invoice']
                   })).then(function(result) {
                       if (result.length) {
                            for (var i=0; i<result.length; i++) {
                                _.each(result[i], function(value, key) {
                                    if (value instanceof Array) {
                                        result[i][key] = value[0];
                                    } else {
                                        result[i][key] = value;
                                    }
                                });
                            }
                            //Need to call onchange_account_id because it updated keys of default_get
                            return (new instance.web.Model("hr.analytic.timesheet").call("on_change_account_id", [[], result[0].account_id,
                                new instance.web.CompoundContext({'user_id': self.parent.get('user_id')})])).then(function(onchange_account) {
                                    var last_day_data = self.get_last_day_data(result);
                                    data_to_copy = _.groupBy(last_day_data, "account_id");
                                    onchange_result = onchange_account.value;
                                    def.resolve().promise();
                            });
                       }
                   });
               }
           });
        } else {
            def.resolve().promise();
        }

        $.when(def).then(function() {
            self.copy_data(data_to_copy, onchange_result);
        });
    },
    copy_data: function(data, onchange_result) {
        var self = this;

        var count = this.get('count');
        self.days[count].account_group = data;
        self.days[count].account_defaults = _.extend({}, this.parent.default_get, onchange_result);
        _.each(self.days[count].account_group, function(account) {
            var d = moment(self.days[count].day).format("YYYY-MM-DD");
            _.each(account,function(account) {
                account.id = undefined;
                account.date = d;
                account.name = self.parent.description_line;
                account.date_start = false;
                account.date_diff_hour = account.date_diff_minute = 0;
            });
        });
        //TODO: Switching view doesn't reflected with copied data
        this.parent.sync();
        self.parent.initialize_content();
    },
    start_interval: function(){
        var self = this;
        if (self.$el.find("i.start_clock").length) {
            self.intervalTimer = setInterval(function(){
                self.$el.find("i.start_clock").each(function() {
                    var el_hour = $(this).parent().parent().find("span.hour");
                    var el_minute = $(this).parent().parent().find("span.minute");
                    var minute = parseInt(el_minute.text()) + 1;
                    if(minute > 60) {
                        el_hour.text(parseInt(el_hour.text()) + 1);
                        minute = 0;
                    }
                    el_minute.text(minute);
                });
            }, 60000);
        }
    },
    get_current_UTCDate: function() {
        var d = new Date();
        return d.getUTCFullYear() +"-"+ (d.getUTCMonth()+1) +"-"+d.getUTCDate()+" "+d.getUTCHours()+":"+d.getUTCMinutes()+":"+d.getUTCSeconds();//+"."+d.getUTCMilliseconds();
    },
    get_date_diff: function(new_date, old_date){
        var difference = Date.parse(new_date).getTime() - Date.parse(old_date).getTime();
        return Math.floor(difference / 3600000 % 60) + ":" + Math.floor(difference / 60000 % 60);
    },
    timer: function(e) {
        var self = this;
        var def = $.Deferred();
        var count = this.get('count');
        var day_count = this.$(e.currentTarget).attr("data-day-count") || this.$(e.srcElement).attr("data-day-count");
        var account_id = this.$(e.currentTarget).attr("data-account");
        var $span = this.$('.oe_timer[data-account="' + account_id + '"][data-day-count="' + day_count + '"]'); 
        var current_account = this.days[count].account_group[account_id];
        var el_clock = $span.find(".oe_timer_clock");
        if (!el_clock.hasClass("start_clock")) {
            //Ensure all other timers are stopped, at a time one timer should run
             new instance.web.DataSetSearch(this, 'hr.analytic.timesheet', this.parent.view.dataset.get_context(),
                [['user_id','=',self.parent.get('user_id')],['date_start', '!=', false]])
                .read_slice(['id', 'date_start', 'unit_amount'], {}).done(function(result){
                    _.each(result, function(timesheet){
                        var unit_amount = timesheet.unit_amount + self.parent.parse_client(self.get_date_diff(self.get_current_UTCDate(), timesheet.date_start));
                        new instance.web.Model("hr.analytic.timesheet").call('write',[[timesheet.id], {'date_start' : false, 'unit_amount' : unit_amount}]);
                    });
                }).done(function(){
                    _.each(self.days, function(day) {
                        _.each(day.account_group, function(account) {
                            if(account[0].date_start){
                                account[0].unit_amount += self.parent.parse_client(self.get_date_diff(self.get_current_UTCDate(), account[0].date_start));
                                account[0].date_start = false;
                                account[0].date_diff_hour = account.date_diff_minute = 0;
                            }
                        });
                    });
                    current_account[0].date_start = self.get_current_UTCDate();
                    def.resolve();
                });
        } else {
            if (self.intervalTimer) {
                clearInterval(self.intervalTimer);
            }
            current_account[0].unit_amount += self.parent.parse_client(self.get_date_diff(self.get_current_UTCDate(), current_account[0].date_start));
            current_account[0].date_start = false;
            def.resolve();
        }
        $.when(def).then(function() {
            self.parent.sync();
            current_account[0].date_diff_hour = current_account[0].date_diff_minute = 0;
            ret = self.parent.view.save().done(function() {
                self.parent.view.reload(); //Need to reload view so that one2many have newly created ids in sheet or we should reload only timesheet_ids field, or do not display button on unsaved record
            });
        });
    },
    toggle_active: function(day_count) {
        this.$el.find(".oe_nav_button[data-day-counter|="+day_count+"]").addClass("oe_active_day").siblings().removeClass("oe_active_day");
    },
    on_delete_line: function(e) {
        if (!confirm(_t("Are you sure you want to delete lines of account, note that this will delete all lines of selected account in current day."))) {
            return;
        }
        var account_id = parseInt($(e.target).data("account"));
        var count = this.get("count");
        var initial_o2m_value = this.generate_o2m_value();
        var day = _.find(this.days, function(day) { return day.day_index === count; });
        delete day.account_group[account_id];
        var ops = this.generate_o2m_value();
        this.parent.unlink_sheets_records(initial_o2m_value, ops);
    },
    on_change_account: function(old_account_id, current_account_id) {
        var self = this;
        var day_count = this.get("count");
        if (old_account_id === current_account_id) {
            return;
        }
        account_group = _.find(this.days[day_count].account_group, function(account_value, account_id) { return account_id == old_account_id;});
        return new instance.web.Model("hr.analytic.timesheet").call("on_change_account_id", [[], current_account_id]).then(function(res) {
            delete self.days[day_count].account_group[old_account_id];
            self.days[day_count].account_group[current_account_id] = account_group;
            _.each(account_group, function(account_line) {
                _.extend(account_line, res.value, {account_id: current_account_id});
            });
            var ops = self.generate_o2m_value();
            self.parent.set({"sheets": ops});
        });
    },
    navigateAll: function(e){
        var self = this;
        if (this.parent.dfm || this.parent.dfms.length)
            this.parent.destroy_content();
        var navigate = $(e.target).data("navigate");
        if (navigate == "prev_day")
            this.navigatePrev();
        else if (navigate == "next_day")
            this.navigateNext();
        else if (navigate == "to_day") {
            for(var i = 0; i < this.days.length; i++) {
                if (_.isEqual(moment(this.days[i].day).format("YYYY/M/d"), moment(new Date()).format("YYYY/M/d"))) {
                    this.update_count(i);
                    break;
                }
            }
        } else {
            this.navigateDays(parseInt($(e.target).data("day-counter"), 10));
        }
        this.week_count = this.days[this.get('count')].week_count;
        this.parent.display_data(this.options);
    },
    update_count: function (count) {
        this.set('week_count', this.days[count].week_count);
        this.set('count', count);
    },
    navigateNext: function() {
        if(this.get('count') == this.days.length-1)
            this.update_count(0);
        else 
            this.update_count(this.get('count')+1);
    },
    navigatePrev: function() {
        if (this.get('count')==0) {
            this.update_count(this.days.length-1);
        }
        else {
            this.update_count(this.get('count')-1);
        }
    },
    navigateDays: function(day){
        this.update_count(day);
    },
});

instance.hr_timesheet_sheet.WeeklyTimesheet = instance.web.Widget.extend({
    template: "hr_timesheet_sheet.WeeklyTimesheet",
    events: {
        "click .oe_timesheet_weekly_account a": "go_to",
        "click .oe_timesheet_switch, .oe_timesheet_weekly_day": "do_switch_mode",
        "click .oe_timesheet_weekly .oe_nav_button": "navigateAll",
        "click .oe_copy_accounts a": "copy_accounts",
        "click .oe_delete_line": "on_delete_account",
    },
    init: function (parent, options) {
        var self = this;
        this.parent = parent;
        this._super(parent);
        this.options = options || {};
        this.set('effective_readonly', this.parent.get("effective_readonly"));
        this.dates = parent.dates;
        this.accounts = parent.accounts;
        this.account_names = parent.account_names;
        this.default_get = parent.default_get;
        this.account_defaults = parent.account_defaults;
        var count = 0;
        var previous_week = false;
        this.days = _.map(parent.dates, function(date, index) {
            var week = moment(date).week();
            if (week != previous_week) {
                count += 1;
            }
            previous_week = week;
            var day = {date: date, day_index: index, week_count: count};
            return day;
        });
        this.on("change:week_count", this, function() {
            _.extend(self.options, {'week_count': this.get('week_count')});
            self.parent.options = self.options;
        });
        if (!options || (options && !options.week_count)) {
            this.week_count = _.first(_.map(this.days, function(day) {return day.week_count;}));
            this.set('week_count', this.week_count);
        } else {
            this.set('week_count', (options || {}).week_count || 0);
        }
    },
    start: function() {
        this.display_data();
    },
    go_to: function(event) {
        this.parent.go_to(event);
    },
    display_data: function() {
        var self = this;
        _.each(self.accounts, function(account) {
            if (!self.parent.get('effective_readonly')) {
                var account_id = account.account;
                var account_m2o = self.parent.init_account(_.pluck(self.accounts, "account"));
                var placeholder_element = self.parent.get_account_placeholder(account_id);
                account_m2o.replace(placeholder_element);
                account_m2o.set_value(account_id);
                account_m2o.current_value = account_m2o.old_value = account_id;
                account_m2o.on("change:value", this, function() {
                    if (account_m2o.get('value') === false) {
                        account_m2o.field_manager.set({display_invalid_fields: true});
                        return;
                    }
                    account_m2o.old_value = account_m2o.current_value;
                    //New record will set false in the current value and when new record is set old value = new value(i.e. false)
                    if (account_m2o.get('value')) {
                        account_m2o.current_value = account_m2o.get('value');
                        self.on_change_account(account_m2o.old_value, account_m2o.current_value);
                    }
                });
            }
            _.each(account.days, function(day, day_count) {
                if (!self.parent.get('effective_readonly')) {
                    self.parent.get_box(account.account, day.day_index).val(self.sum_box(account, day.day_index, true)).change(function() {
                        var num = $(this).val();
                        if (self.parent.is_valid_value(num)){
                            num = (num == 0)?0:Number(self.parent.parse_client(num));
                        }
                        if (isNaN(num)) {
                            $(this).val(self.sum_box(account, day.day_index, true));
                        } else {
                            account.days[day_count].lines[0].unit_amount += num - self.sum_box(account, day.day_index);
                            var product = (account.days[day_count].lines[0].product_id instanceof Array) ? account.days[day_count].lines[0].product_id[0] : account.days[day_count].lines[0].product_id;
                            var journal = (account.days[day_count].lines[0].journal_id instanceof Array) ? account.days[day_count].lines[0].journal_id[0] : account.days[day_count].lines[0].journal_id;
                            self.parent.defs.push(new instance.web.Model("hr.analytic.timesheet").call("on_change_unit_amount", [[], product, account.days[day_count].lines[0].unit_amount, false, false, journal]).then(function(res) {
                                account.days[day_count].lines[0]['amount'] = res.value.amount || 0;
                                self.display_totals();
                                self.parent.sync();
                            }));
                            if(!isNaN($(this).val())){
                                $(this).val(self.sum_box(account, day.day_index, true));
                            }
                        }
                    });
                } else {
                    self.parent.get_box(account.account, day.day_index).html(self.sum_box(account, day.day_index, true));
                }
            });
        });
        self.display_totals();
        self.$(".oe_timesheet_weekly_adding a").click(_.bind(this.parent.init_add_account, this.parent, instance.web.date_to_str(self.dates[0]), _.pluck(self.accounts, "account")));
    },
    get_current_week_data: function(records) {
        var week_count = this.get('week_count');
        if (!records) {
            return;
        }
        var groupby_week = _.groupBy(this.days, "week_count");
        var current_week_dates = groupby_week[week_count];
        var groupby_day_name = _.groupBy(current_week_dates, function(date) { return moment(date.date).format("dddd"); });
        var get_max_date = function(initial_date) {
            _.each(records, function(record) {
                if (moment(record.date).isAfter(initial_date)) {
                    initial_date = moment(record.date);
                }
            });
            return initial_date;
        };
        //Find 7 days range for the week and retrieve last 7 days record from records
        var max_date = get_max_date(moment(records[0].date));
        var start_date = _.clone(max_date);
        start_date = moment(start_date).subtract(7, "days");
        var last_seven_days_records = _.filter(records, function(record) {
            return (moment(record.date).isAfter(start_date) && moment(record.date).isBefore(max_date)) || (moment(record.date).isSame(max_date) || (moment(record.date).isSame(start_date)));
        });

        //Find current week days and replace current weeks date in records by matchin 'Day Name'(ask of HMO)
        current_week_data = _.filter(last_seven_days_records, function(record) {
            return _.has(groupby_day_name, moment(record.date).format("dddd"));
        });
        _.each(current_week_data, function(record) {
            var day = groupby_day_name[moment(record.date).format("dddd")];
            record.date = moment(day[0].date).format("YYYY-MM-DD");
        });
        return current_week_data;
    },
    copy_accounts: function() {
        /*
         * The method will fetch the last timesheet and from the last timesheet it slice the records for current week,
         * this will call get_current_week_data method which do mapping of data, data of last timesheet's Monday will be 
         * placed in current week's Monday and so on...
         * */
        var self = this;
        var data_to_copy;
        var onchange_result = {};
        //Copy Button will be displayed only if there is no accounts in current timesheet in week mode,
        //Because in week mode if there is an account it will be displayed in all weeks, so we only need to consider scenario of fetch last timesheet 7 days
        (new instance.web.Model("hr_timesheet_sheet.sheet").call("search_read", {
           domain: [['user_id','=',self.parent.get('user_id')], ['date_from', '<=', self.parent.field_manager.get_field_value("date_from")]],
           fields: ['timesheet_ids'],
           order: "date_from DESC",
           limit: 1
        })).then(function(result) {
           if (result.length && result[0].timesheet_ids) {
               (new instance.web.Model('hr.analytic.timesheet').call('read', {
                   ids: result[0].timesheet_ids,
                   fields: ['name', 'amount', 'unit_amount', 'date', 'account_id', 'date_start', 'general_account_id', 'journal_id', 'user_id', 'product_id', 'product_uom_id', 'to_invoice']
               })).then(function(result) {
                   if (result.length) {
                        for (var i=0; i<result.length; i++) {
                            _.each(result[i], function(value, key) {
                                if (value instanceof Array) {
                                    result[i][key] = value[0];
                                } else {
                                    result[i][key] = value;
                                }
                            });
                        }
                        //Need to call onchange_account_id because it updated keys of default_get
                        return (new instance.web.Model("hr.analytic.timesheet").call("on_change_account_id", [[], result[0].account_id,
                            new instance.web.CompoundContext({'user_id': self.parent.get('user_id')})])).then(function(onchange_account) {
                                var current_week_data = self.get_current_week_data(result);
                                data_to_copy = _.groupBy(current_week_data, "account_id");
                                onchange_result = onchange_account.value;
                                self.copy_data(data_to_copy);
                        });
                   }
               });
           }
       });
    },
    copy_data: function(accounts, onchange_result) {
        var self = this;
        accounts = _(accounts).chain().map(function(lines, account_id) {
            _.extend({}, this.parent.default_get, onchange_result);
            account_defaults = _.extend({}, this.parent.default_get, onchange_result || {});
            // group by days
            account_id = account_id === "false" ? false :  Number(account_id);
            var group_by_date = _.groupBy(lines, "date");
            var days = _.map(self.parent.dates, function(date, index) {
                var day = {day: date, lines: group_by_date[instance.web.date_to_str(date)] || [], day_index: index, week: moment(date).week()};
                // add line where we will insert/remove hours
                var to_add = _.find(day.lines, function(line) { return line.name === self.description_line;});
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
        _.extend(this.accounts, accounts);
        //TODO: Test Switching view reflected with copied data ?
        this.parent.sync();
        self.parent.initialize_content();
    },
    do_switch_mode: function(e) {
        var index = $(e.currentTarget).attr("data-day-counter");
        if(index)
            this.parent.do_switch_mode(e, {mode: "day", count: parseInt(index), week_count: this.days[index].week_count});
        else
            this.parent.do_switch_mode(e);
    },
    sum_box: function(account, day_count, show_value_in_hour) {
        var line_total = 0;
        _.each(account.days[day_count].lines, function(line) {
            line_total += line.unit_amount;
        });
        return (show_value_in_hour && line_total != 0)?this.parent.format_client(line_total):line_total;
    },
    get_total: function(account) {
        return this.$('[data-account-total="' + account + '"]');
    },
    get_day_total: function(day_count) {
        return this.$('[data-day-total="' + day_count + '"]');
    },
    get_week_total: function() {
        return this.$('.oe_timesheet_weekly_supertotal');
    },
    get_super_total: function() {
        return this.$('.oe_timesheet_weekly_super_total');
    },
    display_totals: function() {
        var self = this;
        var day_tots = _.map(_.range(self.dates.length), function() { return 0; });
        var week_tot = 0;
        var super_total = 0;
        _.each(self.accounts, function(account) {
            var acc_tot = 0;
            _.each(self.days, function(day) {
                var sum = self.sum_box(account, day.day_index);
                if (day.week_count == self.get('week_count')) {
                    acc_tot += sum;
                    day_tots[day.day_index] += sum;
                    week_tot += sum;
                }
                super_total += sum;
            });
            self.get_total(account.account).html(self.parent.format_client(acc_tot));
        });
        _.each(_.range(self.dates.length), function(day_count) {
            self.get_day_total(day_count).html(self.parent.format_client(day_tots[day_count]));
        });
        self.get_week_total().html(self.parent.format_client(week_tot));
        self.get_super_total().html("Total <br/><small>" + self.parent.format_client(super_total));
    },
    generate_o2m_value: function() {
        var self = this;
        var ops = [];
        var ignored_fields = self.parent.ignore_fields();
        _.each(self.accounts, function(account) {
            var auth_keys = _.extend(_.clone(account.account_defaults), {
                id: true, name: true, amount:true, unit_amount: true, date: true, account_id:true, date_start: true,
            });
            _.each(account.days, function(day) {
                _.each(day.lines, function(line) {
                    //if (line.unit_amount !== 0) {
                        var tmp = _.clone(line);
                        //tmp.id = undefined;
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
                        tmp = _.omit(tmp, ignored_fields);
                        ops.push(tmp);
                    //}
                });
            });
        });
        return ops;
    },
    on_delete_account: function(e) {
        var account_id = parseInt($(e.target).data("account"));
        if (!confirm(_t("Are you sure ? you want to delete all lines of this account, note that this will all lines of selected account."))) {
            return;
        }
        var initial_o2m_value = this.generate_o2m_value();
        this.accounts = _.reject(this.accounts, function(account) { return account.account === account_id;});
        var ops = this.generate_o2m_value();
        this.parent.unlink_sheets_records(initial_o2m_value, ops);
    },
    on_change_account: function(old_account_id, current_account_id) {
        var self = this;
        if (old_account_id === current_account_id) {
            return;
        }
        account = _.find(this.accounts, function(account) {return account.account == old_account_id;});
        return new instance.web.Model("hr.analytic.timesheet").call("on_change_account_id", [[], current_account_id]).then(function(res) {
            _.extend(account, {account: current_account_id});
            _.each(account.days, function(day) {
                _.each(day.lines, function(line) {
                    _.extend(line, res.value, {account_id: current_account_id});
                });
            });
            var ops = self.generate_o2m_value();
            self.parent.set({"sheets": ops});
        });
    },
    navigateAll: function(e){
        var self = this;
        if (this.parent.dfm || this.parent.dfms.length)
            this.parent.destroy_content();
        var navigate = $(e.target).data("navigate");
        if (navigate == "prev_week")
            this.navigatePrev();
        else if (navigate == "next_week")
            this.navigateNext();
        else if (navigate == "this_week") {
            for(var i = 0; i < this.days.length; i++) {
                if (_.isEqual(moment(this.days[i].date).week(), moment(new Date()).week())) {
                    this.update_week_count(this.days[i].week_count);
                    break;
                }
            }
        }
        this.parent.display_data(this.options);
    },
    update_week_count: function(count) {
        this.set('week_count', count);
    },
    navigateNext: function() {
        if(this.get('week_count') == _.last(_.map(this.days, function(day) {return day.week_count;})))
            this.update_week_count(this.days[0].week_count);
        else 
            this.update_week_count(this.get('week_count')+1);
    },
    navigatePrev: function() {
        if (this.get('week_count') == _.first(_.map(this.days, function(day) {return day.week_count;}))) {
            this.update_week_count(this.days[this.days.length-1].week_count);
        }
        else {
            this.update_week_count(this.get('week_count')-1);
        }
    },
});
instance.web.form.custom_widgets.add('timesheet', 'instance.hr_timesheet_sheet.Timesheet');
};
