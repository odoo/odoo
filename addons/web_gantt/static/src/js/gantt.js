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
    start: function() {
        return this.rpc("/web/view/load", {"model": this.dataset.model, "view_id": this.view_id, "view_type": "gantt"}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data;
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
                            all_events[mod_id] = {'parent': "", 'evt':[mod_id , grp_key, start_date, start_date, 100, ""]};
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
                            all_events[ch_mod_id] = {'parent': mod_id, 'evt':[ch_mod_id , grp_key, start_date, start_date, 100, ""]};
                            mod_id = ch_mod_id;
                        }
                        else{
                            mod_id = child_event[mod_id][grp_key];
                            temp_id = mod_id;
                        }
                    }
                }
                all_events[id] = {'parent': temp_id, 'evt':[id , text, start_date, duration, 100, ""]};
                final_events.push(id);
            }
            else {
                if (i == 0) {
                    var mod_id = "_" + i;
                    all_events[mod_id] = {'parent': "", 'evt': [mod_id, this.name, start_date, start_date, 100, ""]};
                }
                all_events[id] = {'parent': mod_id, 'evt':[id , text, start_date, duration, 100, ""]};
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
