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
        this._super.apply(this, arguments);
        this.has_been_loaded = $.Deferred();
        this.chart_id = _.uniqueId();
    },
    on_loaded: function(fields_view_get, fields_get) {
        var self = this;
        this.fields_view = fields_view_get;
        this.$el.addClass(this.fields_view.arch.attrs['class']);
        return this.rpc("/web/searchview/fields_get", {"model": this.dataset.model}).pipe(function(fields_get) {
            self.fields = fields_get.fields;
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
        var fields = _.compact(_.map(["date_start", "date_delay", "date_stop"], function(key) {
            return self.fields_view.arch.attrs[key] || '';
        }));
        fields = _.uniq(fields.concat(n_group_bys));
        
        return $.when(this.has_been_loaded).pipe(function() {
            return self.dataset.read_slice(fields, {
                domain: domains,
                context: contexts
            }).pipe(function(data) {
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
        return this.dataset.name_get(ids).pipe(function(names) {
            var ntasks = _.map(tasks, function(task) {
                return _.extend({__name: _.detect(names, function(name) { return name[0] == task.id; })[1]}, task); 
            });
            return self.on_data_loaded_2(ntasks, group_bys);
        });
    },
    on_data_loaded_2: function(tasks, group_bys) {
        var self = this;
        $(".oe_gantt", this.$el).html("");
        
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
        
        // track ids of task items for context menu
        var task_ids = {};
        // creation of the chart
        var generate_task_info = function(task, plevel) {
            var level = plevel || 0;
            if (task.__is_group) {
                var task_infos = _.compact(_.map(task.tasks, function(sub_task) {
                    return generate_task_info(sub_task, level + 1);
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
                var group_name = instance.web.format_value(task.name, self.fields[group_bys[level]]);
                if (level == 0) {
                    var group = new GanttProjectInfo(_.uniqueId("gantt_project_"), group_name, task_start);
                    _.each(task_infos, function(el) {
                        group.addTask(el.task_info);
                    });
                    return group;
                } else {
                    var group = new GanttTaskInfo(_.uniqueId("gantt_project_task_"), group_name, task_start, duration, 100);
                    _.each(task_infos, function(el) {
                        group.addChildTask(el.task_info);
                    });
                    return {task_info: group, task_start: task_start, task_stop: task_stop};
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
                        return;
                } else { // we assume date_duration is defined
                    var tmp = instance.web.format_value(task[self.fields_view.arch.attrs.date_delay],
                        self.fields[self.fields_view.arch.attrs.date_delay]);
                    if (!tmp)
                        return;
                    task_stop = task_start.clone().addMilliseconds(tmp * 60 * 60 * 1000);
                }
                var duration = (task_stop.getTime() - task_start.getTime()) / (1000 * 60 * 60);
                var id = _.uniqueId("gantt_task_");
                var task_info = new GanttTaskInfo(id, task_name, task_start, ((duration / 24) * 8), 100);
                task_info.internal_task = task;
                task_ids[id] = task_info;
                return {task_info: task_info, task_start: task_start, task_stop: task_stop};
            }
        }
        var gantt = new GanttChart();
        _.each(_.compact(_.map(groups, function(e) {return generate_task_info(e, 0);})), function(project) {
            gantt.addProject(project);
        });
        gantt.setEditable(true);
        gantt.setImagePath("/web_gantt/static/lib/dhtmlxGantt/codebase/imgs/");
        gantt.attachEvent("onTaskEndDrag", function(task) {
            self.on_task_changed(task);
        });
        gantt.attachEvent("onTaskEndResize", function(task) {
            self.on_task_changed(task);
        });
        gantt.create(this.chart_id);
        
        // bind event to display task when we click the item in the tree
        $(".taskNameItem", self.$el).click(function(event) {
            var task_info = task_ids[event.target.id];
            if (task_info) {
                self.on_task_display(task_info.internal_task);
            }
        });
        if (this._is_action_enabled('create')) {        
            // insertion of create button
            var td = $($("table td", self.$el)[0]);
            var rendered = QWeb.render("GanttView-create-button");
            $(rendered).prependTo(td);
            $(".oe_gantt_button_create", this.$el).click(this.on_task_create);
        }
    },
    on_task_changed: function(task_obj) {
        var self = this;
        var itask = task_obj.TaskInfo.internal_task;
        var start = task_obj.getEST();
        var duration = (task_obj.getDuration() / 8) * 24;
        var end = start.clone().addMilliseconds(duration * 60 * 60 * 1000);
        var data = {};
        data[self.fields_view.arch.attrs.date_start] =
            instance.web.auto_date_to_str(start, self.fields[self.fields_view.arch.attrs.date_start].type);
        if (self.fields_view.arch.attrs.date_stop) {
            data[self.fields_view.arch.attrs.date_stop] = 
                instance.web.auto_date_to_str(end, self.fields[self.fields_view.arch.attrs.date_stop].type);
        } else { // we assume date_duration is defined
            data[self.fields_view.arch.attrs.date_delay] = duration;
        }
        this.dataset.write(itask.id, data).then(function() {
            console.log("task edited");
        });
    },
    on_task_display: function(task) {
        var self = this;
        var pop = new instance.web.form.FormOpenPopup(self);
        pop.on_write_completed.add_last(function() {
            self.reload();
        });
        pop.show_element(
            self.dataset.model,
            task.id,
            null,
            {}
        );
    },
    on_task_create: function() {
        var self = this;
        var pop = new instance.web.form.SelectCreatePopup(this);
        pop.on_select_elements.add_last(function() {
            self.reload();
        });
        pop.select_element(
            self.dataset.model,
            {
                initial_view: "form",
            }
        );
    },
});

};
