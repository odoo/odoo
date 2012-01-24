/*---------------------------------------------------------
 * OpenERP web_gantt
 *---------------------------------------------------------*/
openerp.web_gantt = function (openerp) {
var _t = openerp.web._t,
   _lt = openerp.web._lt;
var QWeb = openerp.web.qweb;
openerp.web.views.add('gantt', 'openerp.web_gantt.GanttView');

openerp.web_gantt.GanttView = openerp.web.View.extend({
    display_name: _lt('Gantt'),
    template: "GanttView",
    init: function() {
        this._super.apply(this, arguments);
        this.has_been_loaded = $.Deferred();
        this.chart_id = _.uniqueId();
    },
    start: function() {
        return $.when(this.rpc("/web/view/load", {"model": this.dataset.model, "view_id": this.view_id, "view_type": "gantt"}),
            this.rpc("/web/searchview/fields_get", {"model": this.dataset.model})).pipe(this.on_loaded);
    },
    on_loaded: function(fields_view, fields_get) {
        this.fields_view = fields_view[0];
        this.fields = fields_get[0].fields;
        this.field_name = 'name';
        
        this.has_been_loaded.resolve();
    },
    do_search: function (domains, contexts, group_bys) {
        var self = this;
        // select the group by
        var n_group_bys = [];
        if (this.fields_view.arch.attrs.default_group_by) {
            n_group_bys = this.fields_view.arch.attrs.default_group_by.split(',');
        }
        if (group_bys.length) {
            n_group_bys = group_bys;
        }
        // gather the fields to get
        var fields = _.compact(_.map(["date_start", "date_delay", "date_stop", "color", "colors"], function(key) {
            return self.fields_view.arch.attrs[key] || '';
        }));
        fields = _.uniq(fields.concat([this.field_name], n_group_bys));
        
        return $.when(this.has_been_loaded).pipe(function() {
            return self.dataset.read_slice(fields, {
                domain: domains,
                context: contexts
            }).pipe(function(data) {
                return self.on_data_loaded(data, n_group_bys);
            });
        });
    },
    on_data_loaded: function(tasks, group_bys) {
        var self = this;
        $(".oe-gantt-view-view", this.$element).html("");
        
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
                var group_name = openerp.web.format_value(task.name, self.fields[group_bys[level]]);
                if (level == 0) {
                    var group = new GanttProjectInfo(_.uniqueId(), group_name, task_start);
                    _.each(task_infos, function(el) {
                        group.addTask(el.task_info);
                    });
                    return group;
                } else {
                    var group = new GanttTaskInfo(_.uniqueId(), group_name, task_start, duration, 100);
                    _.each(task_infos, function(el) {
                        group.addChildTask(el.task_info);
                    });
                    return {task_info: group, task_start: task_start, task_stop: task_stop};
                }
            } else {
                var task_name = openerp.web.format_value(task[self.field_name], self.fields[self.field_name]);
                var task_start = openerp.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_start]);
                if (!task_start)
                    return;
                var task_stop;
                if (self.fields_view.arch.attrs.date_stop) {
                    task_stop = openerp.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_stop]);
                    if (!task_stop)
                        return;
                } else { // we assume date_duration is defined
                    var tmp = openerp.web.format_value(task[self.fields_view.arch.attrs.date_delay],
                        self.fields[self.fields_view.arch.attrs.date_delay]);
                    if (!tmp)
                        return;
                    task_stop = task_start.clone().addMilliseconds(tmp * 60 * 60 * 1000);
                }
                var duration = (task_stop.getTime() - task_start.getTime()) / (1000 * 60 * 60);
                if (task.id == 23)
                    console.log("loading", task.id, task_start.toString(), task_start.clone().addMilliseconds(duration * 60 * 60 * 1000).toString());
                var task_info = new GanttTaskInfo(_.uniqueId(), task_name, task_start, duration, 100);
                task_info.internal_task = task;
                return {task_info: task_info, task_start: task_start, task_stop: task_stop};
            }
        }
        var gantt = new GanttChart();
        _.each(_.compact(_.map(groups, function(e) {return generate_task_info(e, 0);})), function(project) {
            gantt.addProject(project);
        });
        gantt.setEditable(true);
        gantt.setImagePath("/web_gantt/static/lib/dhtmlxGantt/codebase/imgs/");
        gantt.create(this.chart_id);
        gantt.attachEvent("onTaskEndDrag", function(task) {
            self.on_task_changed(task);
        });
        gantt.attachEvent("onTaskEndResize", function(task) {
            self.on_task_changed(task);
        });
    },
    on_task_changed: function(task_obj) {
        var self = this;
        var itask = task_obj.TaskInfo.internal_task;
        var start = task_obj.getEST();
        var end = task_obj.getFinishDate();
        var duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
        console.log("saving", itask.id, start.toString(), end.toString());
        var data = {};
        data[self.fields_view.arch.attrs.date_start] =
            openerp.web.auto_date_to_str(start, self.fields[self.fields_view.arch.attrs.date_start].type);
        if (self.fields_view.arch.attrs.date_stop) {
            data[self.fields_view.arch.attrs.date_stop] = 
                openerp.web.auto_date_to_str(end, self.fields[self.fields_view.arch.attrs.date_stop].type);
        } else { // we assume date_duration is defined
            data[self.fields_view.arch.attrs.date_delay] = duration;
        }
        this.dataset.write(itask.id, data).then(function() {
            console.log("task edited");
        });
    },
});

openerp.web_gantt.GanttViewOld = openerp.web.View.extend({
    display_name: _lt('Gantt'),

    init: function(parent, dataset, view_id) {
        this._super(parent);
        this.view_manager = parent || new openerp.web.NullViewManager();
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.domain = this.dataset.domain || [];
        this.context = this.dataset.context || {};
        this.has_been_loaded = $.Deferred();
    },

    start: function() {
        this._super();
        return this.rpc("/web/view/load", {"model": this.model, "view_id": this.view_id, "view_type": "gantt"}, this.on_loaded);
    },

    on_loaded: function(data) {

        this.fields_view = data,
        this.name =  this.fields_view.arch.attrs.string,
        this.view_id = this.fields_view.view_id,
        this.fields = this.fields_view.fields;
        
        this.date_start = this.fields_view.arch.attrs.date_start,
        this.date_delay = this.fields_view.arch.attrs.date_delay,
        this.date_stop = this.fields_view.arch.attrs.date_stop,
        this.progress = this.fields_view.arch.attrs.progress,
        this.day_length = this.fields_view.arch.attrs.day_length || 8;

        this.color_field = this.fields_view.arch.attrs.color,
        this.colors = this.fields_view.arch.attrs.colors;
        
        if (this.fields_view.arch.children.length) {
            var level = this.fields_view.arch.children[0];
            this.parent = level.attrs.link, this.text = level.children.length ? level.children[0].attrs.name : level.attrs.name;
        } else {
            this.text = 'name';
        }
        
        if (!this.date_start) {
            console.error("date_start is not defined in the definition of this gantt view");
            return;
        }
        
        this.$element.html(QWeb.render("GanttViewOld", {'height': $('.oe-application-container').height(), 'width': $('.oe-application-container').width()}));
        this.has_been_loaded.resolve();
    },

    init_gantt_view: function() {

        ganttChartControl = this.ganttChartControl = new GanttChart(this.day_length);
        ganttChartControl.setImagePath("/web_gantt/static/lib/dhtmlxGantt/codebase/imgs/");
        ganttChartControl.setEditable(true);
        ganttChartControl.showTreePanel(true);
        ganttChartControl.showContextMenu(false);
        ganttChartControl.showDescTask(true,'d,s-f');
        ganttChartControl.showDescProject(true,'n,d');

    },
    
    project_starting_date : function() {
        var self = this,
            projects = this.database_projects,
            min_date = _.min(projects, function(prj) {
                return self.format_date(prj[self.date_start]);
            });
        if (min_date) this.project_start_date = this.format_date(min_date[self.date_start]);
        else 
            this.project_start_date = Date.today();
        return $.Deferred().resolve().promise();
    },
    
    format_date : function(date) {
        var datetime_regex = /^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)(?:\.\d+)?$/,
            date_regex = /^\d\d\d\d-\d\d-\d\d$/,
            time_regex = /^(\d\d:\d\d:\d\d)(?:\.\d+)?$/,
            def = $.Deferred();
        if(date_regex.exec(date)) {
            this.date_format = "yyyy-MM-dd";
        } else if(time_regex.exec(date)) {
            this.date_format = "HH:mm:ss";
        } else {
            this.date_format = "yyyy-MM-dd HH:mm:ss";
        }
        if(typeof date === 'string')
            return openerp.web.auto_str_to_date(date);
        return date;
    },

    on_project_loaded: function(events) {
        
        if(!events.length) return;
        var self = this;
        var started_projects = _.filter(events, function(res) {
            return !!res[self.date_start];
        });
        
        this.database_projects = started_projects;
        
        if(!self.name && started_projects.length > 0) {
            var name = started_projects[0][self.parent];
            self.name = name instanceof Array? name[name.length - 1] : name;
        }
        this.$element.find('#add_task').click(function() {
            self.editTask();
        });
        
        $.when(this.project_starting_date())
            .then(function() {
                if(self.ganttChartControl) {
                    self.ganttChartControl.clearAll();
                    self.$element.find('#GanttView').empty();
                }
            })
            .done(this.init_gantt_view());
        
        var self = this;
        var show_event = started_projects;
        _.each(show_event, function(evt) {evt[self.date_start] = self.format_date(evt[self.date_start])});
        this.project = new GanttProjectInfo("_1", self.name, this.project_start_date);
        self.ganttChartControl.addProject(this.project);
        //create child
        var k = 0;
        var color_box = {};
        var parents = {};
        var all_events = {};
        var child_event = {};
        var temp_id = "";
        var final_events = [];
        for (var i in show_event) {

            var res = show_event[i];

            var id = res['id'];
            var text = res[this.text];
            var start_date = res[this.date_start];
            var progress = res[this.progress] || 100;

            if (this.date_stop != undefined){
                if (res[this.date_stop] != false){
                    var stop_date = this.convert_str_date(res[this.date_stop]);
                    var duration= self.hours_between(start_date, stop_date);
                }
                else{
                    var duration = 0;
                }
            }
            else{
                var duration = res[this.date_delay];
            }
            if (!duration)
                duration = 0;

            if (this.group_by.length){
                for (var j in self.group_by){
                    var grp_key = res[self.group_by[j]];
                    if (typeof(grp_key) == "object"){
                        grp_key = res[self.group_by[j]][1];
                    }
                    else{
                        grp_key = res[self.group_by[j]];
                    }

                    if (!grp_key){
                        grp_key = "Undefined";
                    }

                    if (j == 0){
                        if (parents[grp_key] == undefined){
                            var mod_id = i+ "_" +j;
                            parents[grp_key] = mod_id;
                            child_event[mod_id] = {};
                            all_events[mod_id] = {'parent': "", 'evt':[mod_id , grp_key, start_date, start_date, progress, ""]};
                        }
                        else{
                            mod_id = parents[grp_key];
                        }
                        temp_id = mod_id;
                    }else{
                        if (child_event[mod_id][grp_key] == undefined){
                            var ch_mod_id = i+ "_" +j;
                            child_event[mod_id][grp_key] = ch_mod_id;
                            child_event[ch_mod_id] = {};
                            temp_id = ch_mod_id;
                            all_events[ch_mod_id] = {'parent': mod_id, 'evt':[ch_mod_id , grp_key, start_date, start_date, progress, ""]};
                            mod_id = ch_mod_id;
                        }
                        else{
                            mod_id = child_event[mod_id][grp_key];
                            temp_id = mod_id;
                        }
                    }
                }
                all_events[id] = {'parent': temp_id, 'evt':[id , text, start_date, duration, progress, ""]};
                final_events.push(id);
            }
            else {
                if (i == 0) {
                    var mod_id = "_" + i;
                    all_events[mod_id] = {'parent': "", 'evt': [mod_id, this.name, start_date, start_date, progress, ""]};
                }
                all_events[id] = {'parent': mod_id, 'evt':[id , text, start_date, duration, progress, ""]};
                final_events.push(id);
            }
        }

        for (var i in final_events){
            var evt_id = final_events[i];
            var evt_date = all_events[evt_id]['evt'][2];
            while (all_events[evt_id]['parent'] != "") {
               var parent_id =all_events[evt_id]['parent'];
               if (all_events[parent_id]['evt'][2] > evt_date){
                    all_events[parent_id]['evt'][2] = evt_date;
               }
               evt_id = parent_id;
            }
        }
        var evt_id = [];
        var evt_date = "";
        var evt_duration = "";
        var evt_end_date = "";
        var project_tree_field = [];
        for (var i in final_events){
            evt_id = final_events[i];
            evt_date = all_events[evt_id]['evt'][2];
            evt_duration = all_events[evt_id]['evt'][3];

            var evt_str_date = this.convert_date_str(evt_date);
            evt_end_date = this.end_date(evt_str_date, evt_duration);

            while (all_events[evt_id]['parent'] != "") {
               var parent_id =all_events[evt_id]['parent'];
               if (all_events[parent_id]['evt'][3] < evt_end_date){
                    all_events[parent_id]['evt'][3] = evt_end_date;
               }
               evt_id = parent_id;
            }
        }

        for (var j in self.group_by) {
            self.render_events(all_events, j);
        }

        if (!self.group_by.length) {
            self.render_events(all_events, 0);
        }

        for (var i in final_events) {
            evt_id = final_events[i];
            res = all_events[evt_id];
            task=new GanttTaskInfo(res['evt'][0], res['evt'][1], res['evt'][2], res['evt'][3], res['evt'][4], "");
            prt = self.project.getTaskById(res['parent']);
            prt.addChildTask(task);
        }

        var oth_hgt = 264;
        var min_hgt = 150;
        var name_min_wdt = 150;
        var gantt_hgt = $(window).height() - oth_hgt;
        var search_wdt = $("#oe_app_search").width();

        if (gantt_hgt > min_hgt) {
            $('#GanttView').height(gantt_hgt).width(search_wdt);
        } else{
            $('#GanttView').height(min_hgt).width(search_wdt);
        }

        self.ganttChartControl.create("GanttView");
        
        // Setup Events
        self.ganttChartControl.attachEvent("onTaskStartDrag", function(task) {
            if (task.parentTask) {
                var task_date = task.getEST();
                if (task_date.getHours()) {
                    task_date.set({
                        hour: task_date.getHours(),
                        minute: task_date.getMinutes(),
                        second: 0
                    });
                }
            }
        });
        self.ganttChartControl.attachEvent("onTaskEndResize", function(task) {return self.resizeTask(task);});
        self.ganttChartControl.attachEvent("onTaskEndDrag", function(task) {return self.resizeTask(task);});
        
        var taskdiv = $("div.taskPanel").parent();
        taskdiv.addClass('ganttTaskPanel');
        taskdiv.prev().addClass('ganttDayPanel');
        var $gantt_panel = $(".ganttTaskPanel , .ganttDayPanel");

        var ganttrow = $('.taskPanel').closest('tr');
        var gtd =  ganttrow.children(':first-child');
        gtd.children().addClass('task-name');

        $(".toggle-sidebar").click(function(e) {
            self.set_width();
        });

        $(window).bind('resize',function() {
            window.clearTimeout(self.ganttChartControl._resize_timer);
            self.ganttChartControl._resize_timer = window.setTimeout(function(){
                self.reloadView();
            }, 200);
        });
        
        var project = self.ganttChartControl.getProjectById("_1");
        if (project) {
            $(project.projectItem[0]).hide();
            $(project.projectNameItem).hide();
            $(project.descrProject).hide();
            
            _.each(final_events, function(id) {
                var Task = project.getTaskById(id);
                $(Task.cTaskNameItem[0]).click(function() {
                    self.editTask(Task);
                })
            });
        }
    },
    
    resizeTask: function(task) {
        var self = this,
            event_id = task.getId();
        if(task.childTask.length)
            return;
        
        var data = {};
        data[this.date_start] = task.getEST().toString(this.date_format);
        
        if(this.date_stop) {
            var diff = task.getDuration() % this.day_length,
                finished_date = task.getFinishDate().add({hours: diff});
            data[this.date_stop] = finished_date.toString(this.date_format);
        } else {
            data[this.date_delay] = task.getDuration();
        }
        this.dataset
            .write(event_id, data, {})
            .done(function() {
                var get_project = _.find(self.database_projects, function(project){ return project.id == event_id});
                _.extend(get_project,data);
                self.reloadView();
            });
    },
    
    editTask: function(task) {
        var self = this,
            event_id;
        if (!task)
            event_id = 0;
        else {
            event_id = task.getId();
            if(!event_id || !task.parentTask)
                return false;
        }
        if(event_id) event_id = parseInt(event_id, 10);
        
        if (!event_id) {
            var pop = new openerp.web.form.SelectCreatePopup(this);
            pop.select_element(
                this.model,
                {
                    title: _t("Create: ") + this.name,
                    initial_view: 'form',
                    disable_multiple_selection: true
                },
                this.dataset.domain,
                this.context || this.dataset.context
            )
            pop.on_select_elements.add_last(function(element_ids) {
                self.dataset.read_ids(element_ids,[]).done(function(projects) {
                    self.database_projects.concat(projects);
                    self.reloadView();
                });
            });
        }
        else {
            var pop = new openerp.web.form.FormOpenPopup(this);
            pop.show_element(this.model, event_id, this.context || this.dataset.context, {'title' : _t("Open: ") + this.name});
            pop.on_write.add(function(id, data) {
                var get_project = _.find(self.database_projects, function(project){ return project.id == id});
                if (get_project) {
                    _.extend(get_project, data);
                } else {
                    _.extend(self.database_projects, _.extend(data, {'id': id}));
                }
                self.reloadView();
            });
        }
    },

    set_width: function() {
        $gantt_panel.width(1);
        jQuery(".ganttTaskPanel").parent().width(1);

        var search_wdt = jQuery("#oe_app_search").width();
        var day_wdt = jQuery(".ganttDayPanel").children().children().width();
        jQuery('#GanttView').css('width','100%');

        if (search_wdt - day_wdt <= name_min_wdt){
            jQuery(".ganttTaskPanel").parent().width(search_wdt - name_min_wdt);
            jQuery(".ganttTaskPanel").width(search_wdt - name_min_wdt);
            jQuery(".ganttDayPanel").width(search_wdt - name_min_wdt - 14);
            jQuery('.task-name').width(name_min_wdt);
            jQuery('.task-name').children().width(name_min_wdt);
        }else{
            jQuery(".ganttTaskPanel").parent().width(day_wdt);
            jQuery(".ganttTaskPanel").width(day_wdt);
            jQuery(".taskPanel").width(day_wdt - 16);
            jQuery(".ganttDayPanel").width(day_wdt -16);
            jQuery('.task-name').width(search_wdt - day_wdt);
            jQuery('.task-name').children().width(search_wdt - day_wdt);
        }

    },

    end_date: function(dat, duration) {

         var self = this;

         var dat = this.convert_str_date(dat);

         var day = Math.floor(duration/self.day_length);
         var hrs = duration % self.day_length;

         dat.add(day).days();
         dat.add(hrs).hour();

         return dat;
    },

    hours_between: function(date1, date2, parent_task) {

        var ONE_DAY = 1000 * 60 * 60 * 24;
        var date1_ms = date1.getTime();
        var date2_ms = date2.getTime();
        var difference_ms = Math.abs(date1_ms - date2_ms);

        var d = parent_task? Math.ceil(difference_ms / ONE_DAY) : Math.floor(difference_ms / ONE_DAY);
        var h = (difference_ms % ONE_DAY)/(1000 * 60 * 60);
        var num = (d * this.day_length) + h;
        return parseFloat(num.toFixed(2));

    },

    render_events : function(all_events, j) {

        var self = this;
        for (var i in all_events){
            var res = all_events[i];
            if ((typeof(res['evt'][3])) == "object"){
                res['evt'][3] = self.hours_between(res['evt'][2],res['evt'][3], true);
            }

            k = res['evt'][0].toString().indexOf('_');

            if (k != -1) {
                if (res['evt'][0].substring(k) == "_"+j){
                    if (j == 0){
                        task = new GanttTaskInfo(res['evt'][0], res['evt'][1], res['evt'][2], res['evt'][3], res['evt'][4], "");
                        self.project.addTask(task);
                    } else {
                        task = new GanttTaskInfo(res['evt'][0], res['evt'][1], res['evt'][2], res['evt'][3], res['evt'][4], "");
                        prt = self.project.getTaskById(res['parent']);
                        prt.addChildTask(task);
                    }
                }
            }
        }
    },

    convert_str_date: function (str) {
        if (typeof str == 'string') {
            if (str.length == 19) {
                this.date_format = "yyyy-MM-dd HH:mm:ss";
                return openerp.web.str_to_datetime(str);
            }
            else 
                if (str.length == 10) {
                    this.date_format = "yyyy-MM-dd";
                    return openerp.web.str_to_date(str);
                }
                else 
                    if (str.length == 8) {
                        this.date_format = "HH:mm:ss";
                        return openerp.web.str_to_time(str);
                    }
            throw "Unrecognized date/time format";
        } else {
            return str;
        }
    },

    convert_date_str: function(full_date) {
        if (this.date_format == "yyyy-MM-dd HH:mm:ss"){
            return openerp.web.datetime_to_str(full_date);
        } else if (this.date_format == "yyyy-MM-dd"){
            return openerp.web.date_to_str(full_date);
        } else if (this.date_format == "HH:mm:ss"){
            return openerp.web.time_to_str(full_date);
        }
        throw "Unrecognized date/time format";
    },
    
    reloadView: function() {
       return this.on_project_loaded(this.database_projects);
    },

    do_search: function (domains, contexts, groupbys) {
        var self = this;
        this.group_by = [];
        if (this.fields_view.arch.attrs.default_group_by) {
            this.group_by = this.fields_view.arch.attrs.default_group_by.split(',');
        }
        
        if (groupbys.length) {
            this.group_by = groupbys;
        }
        var fields = _.compact(_.map(this.fields_view.arch.attrs,function(value,key) {
            if (key != 'string' && key != 'default_group_by') {
                return value || '';
            }
        }));
        fields = _.uniq(fields.concat(_.keys(this.fields), this.text, this.group_by));
        $.when(this.has_been_loaded).then(function() {
                self.dataset.read_slice(fields, {
                    domain: domains,
                    context: contexts
                }).done(function(projects) {
                    self.on_project_loaded(projects);
                });
        });
    },

    do_show: function() {
        this.do_push_state({});
        return this._super();
    }

});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};
// vim:et fdc=0 fdl=0:
