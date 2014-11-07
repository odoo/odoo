/*---------------------------------------------------------
 * OpenERP web_gantt
 *---------------------------------------------------------*/
openerp.web_gantt = function (instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;
instance.web.views.add('gantt', 'instance.web_gantt.GanttView');

instance.web_gantt.GanttView = instance.web.View.extend({
    display_name: _lt('Gantt'),
    template: "GanttView",
    view_type: "gantt",
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.has_been_loaded = $.Deferred();
        this.chart_id = _.uniqueId();
        // Gantt configuration
        gantt.config.autosize = "y";
        gantt.config.scale_offset_minimal = false;
        gantt.config.open_tree_initially = true;
        gantt.config.round_dnd_dates = false;
        gantt.config.drag_links = false,
        gantt.config.drag_progress = false,
        gantt.config.grid_width = 200;
        gantt.config.row_height = 25;
        gantt.config.duration_unit = "hour";
        gantt.config.columns = [{name:"text", label:_t("Gantt View"), tree:true, width:'*' }];
        gantt.templates.grid_folder = function() { return ""; };
        gantt.templates.grid_file = function() { return ""; };
        gantt.templates.grid_indent = function() {
            return "<div class='gantt_tree_indent' style='width:5px;'></div>";
        };
    },
    view_loading: function(r) {
        return this.load_gantt(r);
    },
    load_gantt: function(fields_view_get, fields_get) {
        var self = this;
        this.fields_view = fields_view_get;
        this.$el.addClass(this.fields_view.arch.attrs['class']);
        // Get colors attribute from xml view file.
        if(this.fields_view.arch.attrs.colors) {
            this.colors = _(this.fields_view.arch.attrs.colors.split(';')).chain().compact().map(function(color_pair) {
                var pair = color_pair.split(':'), color = pair[0], expr = pair[1];
                var temp = py.parse(py.tokenize(expr));
                return {'color': color, 'field': temp.expressions[0].value, 'opt': temp.operators[0], 'value': temp.expressions[1].value};
            }).value();
        }
        return self.alive(new instance.web.Model(this.dataset.model)
            .call('fields_get')).then(function (fields) {
                self.fields = fields;
                self.has_been_loaded.resolve();
            });
    },
    do_search: function (domains, contexts, group_bys) {
        var self = this;
        self.last_domains = domains;
        self.last_contexts = contexts;
        self.last_group_bys = group_bys;
        // select the group by
        var n_group_bys = [];
        if (this.fields_view.arch.attrs.default_group_by) {
            n_group_bys = this.fields_view.arch.attrs.default_group_by.split(',');
        }
        if (group_bys.length) {
            n_group_bys = group_bys;
        }
        // gather the fields to get
        var fields = _.compact(_.map(["date_start", "date_delay", "date_stop", "progress"], function(key) {
            return self.fields_view.arch.attrs[key] || '';
        }));
        fields = _.uniq(fields.concat(_.pluck(this.colors, "field").concat(n_group_bys)));
        
        return $.when(this.has_been_loaded).then(function() {
            return self.dataset.read_slice(fields, {
                domain: domains,
                context: contexts
            }).then(function(data) {
                return self.on_data_loaded(data, n_group_bys);
            });
        });
    },
    reload: function() {
        if (this.last_domains !== undefined)
            return this.do_search(this.last_domains, this.last_contexts, this.last_group_bys);
    },
    on_data_loaded: function(tasks, group_bys) {
        var self = this;
        var ids = _.pluck(tasks, "id");
        return this.dataset.name_get(ids).then(function(names) {
            var ntasks = _.map(tasks, function(task) {
                return _.extend({__name: _.detect(names, function(name) { return name[0] == task.id; })[1]}, task); 
            });
            return self.on_data_loaded_2(ntasks, group_bys);
        });
    },
    on_data_loaded_2: function(tasks, group_bys) {
        var self = this;
        this.$el.find(".oe_gantt").html("");

        //prevent more that 1 group by
        if (group_bys.length > 0) {
            group_bys = [group_bys[0]];
        }
        // if there is no group by, simulate it
        if (group_bys.length == 0) {
            group_bys = ["_pseudo_group_by"];
            _.each(tasks, function(el) {
                el._pseudo_group_by = "Gantt View";
            });
            this.fields._pseudo_group_by = {type: "string"};
        }
        
        // get the groups
        var split_groups = function(tasks, group_bys) {
            if (group_bys.length === 0)
                return tasks;
            var groups = [];
            _.each(tasks, function(task) {
                var group_name = task[_.first(group_bys)];
                var group = _.find(groups, function(group) { return _.isEqual(group.name, group_name); });
                if (group === undefined) {
                    group = {name:group_name, tasks: [], __is_group: true};
                    groups.push(group);
                }
                group.tasks.push(task);
            });
            _.each(groups, function(group) {
                group.tasks = split_groups(group.tasks, _.rest(group_bys));
            });
            return groups;
        }
        var groups = split_groups(tasks, group_bys);
        
        // Use scale_zoom attribute in xml file to specify zoom timeline(day,week,month,year), By default month
        var scale = this.fields_view.arch.attrs.scale_zoom;
        if (!_.contains(['day', 'week', 'month', 'year'], scale)) {
            scale = "month";
        }
        this.$el.find("div.btn-group").button('reset');
        this.$el.find("input[value=" + scale + "]").prop("checked", true).parent().addClass("active");
        self.scale_zoom(scale);
        gantt.init(this.chart_id);
        gantt.clearAll();
        this.$el.find(".oe_gantt_button_create").unbind("click");
        gantt.detachAllEvents();
        // call dhtmlxgantt_tooltip.js code, because detachAllEvents() method detach tooltip events.
        call_tooltip();
        var normalize_format = instance.web.normalize_format(_t.database.parameters.date_format);
        gantt.templates.tooltip_text = function(start, end, task) {
            var duration = task.duration / 3;
            if(duration < 1) duration = 1;
            return "<b><u>" + task.text + "</u></b><br/><b>" + _t("Start date") + ":</b> " +
                _t(moment(start).format(normalize_format)) + "<br/><b>" +
                _t("End date") + ":</b> " + _t(moment(end).format(normalize_format)) +
                "<br/><b>" + _t("Duration") + ":</b> " + duration.toFixed(2) + " " + _t("Hours");
        };
        
        var tasks = [];
        var total_percent = 0, total_task = 0;
        // creation of the chart
        var generate_task_info = function(task, plevel, project_id) {
            if (_.isNumber(task[self.fields_view.arch.attrs.progress])) {
                var percent = task[self.fields_view.arch.attrs.progress] || 0;
            } else {
                var percent = 100;
            }
            var level = plevel || 0;
            project_id = project_id || _.uniqueId("gantt_project_");
            if (task.__is_group) {
                var task_infos = _.compact(_.map(task.tasks, function(sub_task) {
                    return generate_task_info(sub_task, level + 1, project_id);
                }));
                if (task_infos.length == 0)
                    return;
                var task_start = _.reduce(_.pluck(task_infos, "task_start"), function(date, memo) {
                    return memo === undefined || date < memo ? date : memo;
                }, undefined);
                var task_stop = _.reduce(_.pluck(task_infos, "task_stop"), function(date, memo) {
                    return memo === undefined || date > memo ? date : memo;
                }, undefined);
                var duration = (task_stop.getTime() - task_start.getTime()) / (1000 * 60 * 60);
                var group_name = task.name ? instance.web.format_value(task.name, self.fields[group_bys[level]]) : "-";
                if (level == 0) {
                    gantt.addTask({
                        'id': project_id,
                        'text': group_name,
                        'start_date': task_start,
                        'duration': ((duration / 24) * 8) * 3 || 1,
                        'progress': total_percent / total_task / 100,
                    });
                    total_task = total_percent = 0;
                    return {task_start: task_start, task_stop: task_stop};
                } else {
                  var id = _.uniqueId("gantt_project_task_");
                  tasks.push({
                      'id': id,
                      'text': group_name,
                      'start_date': task_start,
                      'duration': duration || 1,
                      'progress': percent / 100,
                      'parent': project_id
                  });
                  total_task = total_percent = 0;
                  return {task_start: task_start, task_stop: task_stop};
              }
            } else {
                var task_name = task.__name;
                var task_start = instance.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_start]);
                if (!task_start)
                    return;
                var task_stop;
                if (self.fields_view.arch.attrs.date_stop) {
                    task_stop = instance.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_stop]);
                    if (!task_stop)
                        task_stop = task_start;
                } else { // we assume date_duration is defined
                    var tmp = instance.web.format_value(task[self.fields_view.arch.attrs.date_delay],
                        self.fields[self.fields_view.arch.attrs.date_delay]);
                    if (!tmp)
                        return;
                    var m_task_start = moment(task_start).add(tmp, 'hours');
                    task_stop = m_task_start.toDate();
                }
                var duration = (task_stop.getTime() - task_start.getTime()) / (1000 * 60 * 60);
                total_percent += percent, total_task += 1;
                // Check condition to apply color.
                _.each(self.colors, function(color){
                    if(eval("'" + task[color.field] + "' " + color.opt + " '" + color.value + "'"))
                        self.color = color.color;
                });
                tasks.push({
                    'id': "gantt_task_" + task.id,
                    'text': task_name,
                    'start_date': task_start,
                    'duration': (((duration / 24) * 8) * 3 || 1),
                    'progress': percent / 100,
                    'parent': project_id,
                    'color': self.color
                });
                self.color = undefined;
                return {task_start: task_start, task_stop: task_stop};
            }
        }
        _.each(groups, function(group) { generate_task_info(group, 0); });
        gantt.parse({"data": tasks});
        gantt.attachEvent("onTaskClick", function(id, e){
            if(gantt.hasChild(id)) return true;
            var attr = self.fields_view.arch.attrs;
            if(e.target.className == "gantt_task_content" || e.target.className == "gantt_task_drag task_left" || e.target.className == "gantt_task_drag task_right") {
                if(attr.action) {
                    var actual_id = parseInt(id.split("gantt_task_").slice(1)[0]);
                    if(attr.relative_field) {
                        new instance.web.Model("ir.model.data").call("xmlid_lookup", [attr.action]).done(function(result) {
                            var add_context = {};
                            add_context["search_default_" + attr.relative_field] = actual_id;
                            self.do_action(result[2], {'additional_context': add_context});
                        });
                    }
                    return false;
                }
            }
            self.on_task_display(gantt.getTask(id));
        });
        gantt.attachEvent("onTaskDblClick", function(){ return false; });
        gantt.attachEvent("onBeforeTaskDrag", function(id){
            if(gantt.hasChild(id)) return false;
            return true;
        });
        gantt.attachEvent("onTaskDrag", function(id){
            // Refresh parent when children are resize
            var start_date, stop_date;
            var parent = gantt.getTask(gantt.getTask(id).parent);
            _.each(gantt.getChildren(parent.id), function(task_id){
                var task_start_date = gantt.getTask(task_id).start_date;
                var task_stop_date = gantt.getTask(task_id).end_date;
                if(!start_date) start_date = task_start_date;
                if(!stop_date) stop_date = task_stop_date;
                if(start_date > task_start_date) start_date = task_start_date;
                if(stop_date < task_stop_date) stop_date = task_stop_date;
            });
            parent.start_date = start_date;
            parent.end_date = stop_date;
            gantt.updateTask(parent.id);
        });
        gantt.attachEvent("onAfterTaskDrag", function(id){
            self.on_task_changed(gantt.getTask(id));
        });
        if (this.is_action_enabled('create')) {
            this.$el.find(".oe_gantt_button_create").click(this.on_task_create);
        }
        this.$el.find("div.btn-group label").click(function(e) {
            self.scale_zoom(self.$el.find(e.currentTarget).find("input").val());
            gantt.parse({"data": tasks});
        });
    },
    scale_zoom: function(value) {
        gantt.config.step = 1;
        gantt.config.min_column_width = 50;
        gantt.config.scale_height = 50;
        gantt.templates.scale_cell_class = function(date) {};
        gantt.templates.task_cell_class = function(item, date) {
            if(date.getDay() == 0 || date.getDay() == 6) return "weekend_task";
        };
        gantt.templates.date_scale = null;
        switch (value) {
            case "day":
                gantt.templates.scale_cell_class = function(date) {
                    if(date.getDay() == 0 || date.getDay() == 6) return "weekend_scale";
                };
                gantt.config.scale_unit = "day";
                gantt.config.date_scale = "%d %M";
                gantt.config.subscales = [];
                gantt.config.scale_height = 27;
                break;
            case "week":
                var weekScaleTemplate = function(date){
                    var dateToStr = gantt.date.date_to_str("%d %M %Y");
                    var endDate = gantt.date.add(gantt.date.add(date, 1, "week"), -1, "day");
                        return dateToStr(date) + " - " + dateToStr(endDate);
                };
                gantt.config.scale_unit = "week";
                gantt.templates.date_scale = weekScaleTemplate;
                gantt.config.subscales = [
                    {unit:"day", step:1, date:"%d, %D", css:function(date) {
                        if(date.getDay() == 0 || date.getDay() == 6) return "weekend_scale";
                    } }
                ];
                break;
            case "month":
                gantt.config.scale_unit = "month";
                gantt.config.date_scale = "%F, %Y";
                gantt.config.subscales = [
                    {unit:"day", step:1, date:"%d", css:function(date) {
                        if(date.getDay() == 0 || date.getDay() == 6) return "weekend_scale";
                    } }
                ];
                gantt.config.min_column_width = 25;
                break;
            case "year":
                gantt.config.scale_unit = "year";
                gantt.config.date_scale = "%Y";
                gantt.config.subscales = [
                    {unit:"month", step:1, date:"%M" }
                ];
                gantt.templates.task_cell_class = function(item, date) {};
                break;
        }
    },
    on_task_changed: function(task_obj) {
        var self = this;
        var start = task_obj.start_date;
        var duration = (task_obj.duration / 8) * 24 / 3;
        var end = moment(start).add(duration, 'hours').toDate();
        var data = {};
        data[self.fields_view.arch.attrs.date_start] =
            instance.web.auto_date_to_str(start, self.fields[self.fields_view.arch.attrs.date_start].type);
        if (self.fields_view.arch.attrs.date_stop) {
            data[self.fields_view.arch.attrs.date_stop] = 
                instance.web.auto_date_to_str(end, self.fields[self.fields_view.arch.attrs.date_stop].type);
        } else { // we assume date_duration is defined
            data[self.fields_view.arch.attrs.date_delay] = duration;
        }
        var task_id = parseInt(task_obj.id.split("gantt_task_").slice(1)[0]);
        this.dataset.write(task_id, data);
    },
    on_task_display: function(task) {
        var self = this;
        var task_id = parseInt(task.id.split("gantt_task_").slice(1)[0]);
        var pop = new instance.web.form.FormOpenPopup(self);
        pop.on('write_completed', self, self.reload);
        pop.show_element(
            self.dataset.model,
            task_id,
            null,
            {readonly: true, title: task.text}
        );
        pop.on('closed', self, self.reload);
        var form_controller = pop.view_form;
        form_controller.on("load_record", self, function() {
             var footer = pop.$el.closest(".modal").find(".modal-footer");
             footer.find('.oe_form_button_edit,.oe_form_button_save').remove();
             footer.find(".oe_form_button_cancel").prev().remove();
             footer.find('.oe_form_button_cancel').before("<span> or </span>");
             button_edit = _.str.sprintf("<button class='oe_button oe_form_button_edit oe_bold oe_highlight'><span> %s </span></button>",_t("Edit"));
             button_save = _.str.sprintf("<button class='oe_button oe_form_button_save oe_bold oe_highlight'><span> %s </span></button>",_t("Save"));
             footer.prepend(button_edit + button_save);
             footer.find('.oe_form_button_save').hide();
             footer.find('.oe_form_button_edit').on('click', function() {
                 form_controller.to_edit_mode();
                 footer.find('.oe_form_button_edit,.oe_form_button_save').toggle();
             });
             footer.find('.oe_form_button_save').on('click', function() {
                 form_controller.save();
                 form_controller.to_view_mode();
                 footer.find('.oe_form_button_edit,.oe_form_button_save').toggle();
             });
        });
    },
    on_task_create: function() {
        var self = this;
        var pop = new instance.web.form.SelectCreatePopup(this);
        pop.on("elements_selected", self, function() {
            self.reload();
        });
        pop.select_element(
            self.dataset.model,
            {
                title: _t("Create"),
                initial_view: "form",
            }
        );
    },
});
};
