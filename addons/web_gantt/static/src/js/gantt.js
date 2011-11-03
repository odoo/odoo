/*---------------------------------------------------------
 * OpenERP web_gantt
 *---------------------------------------------------------*/
openerp.web_gantt = function (openerp) {
var _t = openerp.web._t;
var QWeb = openerp.web.qweb;

QWeb.add_template('/web_gantt/static/src/xml/web_gantt.xml');
openerp.web.views.add('gantt', 'openerp.web_gantt.GanttView');
openerp.web_gantt.GanttView = openerp.web.View.extend({

init: function(parent, dataset, view_id) {
        this._super(parent);
        this.view_manager = parent || new openerp.web.NullViewManager();
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.domain = this.dataset.domain || [];
        this.groupby = [];
        this.context = this.dataset.context || {};
        this.has_been_loaded = $.Deferred();
//        this.ganttChartControl = new GanttChart();
        this.COLOR_PALETTE = ['#ccccff', '#cc99ff', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
                 '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
                 '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
                 '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900'];
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
        
        var level = this.fields_view.arch.children[0];
        this.parent = level.attrs.link,
        this.text = level.children.length ? level.children[0].attrs.name : level.attrs.name;
        
        if (!this.date_start) {
            return self.do_warn(_t("date_start is not defined "))
        }
        
        this.$element.html(QWeb.render("GanttView", {'height': $('.oe-application-container').height(), 'width': $('.oe-application-container').width()}));
        this.has_been_loaded.resolve();
    },
    
    on_project_loaded: function(projects) {
        
        if(!projects.length) return;
        var self = this,
            started_projects = _.filter(projects, function(res) {
            return res[self.date_start];
        });
        
        $.when(this.project_starting_date(started_projects), this.project_duration(started_projects), this.calculate_difference())
            .done(function() {
                var Project = new GanttProjectInfo(0, self.name, self.project_start_date),
                    Task = new GanttTaskInfo(0, self.name, self.project_start_date, self.total_duration, 100, "");
                $.when(self.add_tasks(started_projects, Task))
                    .done(function() {
                        self.init_gantt_view(Project, Task);
                    });
            });
    },
    
    project_duration: function(projects) {
        
        var self = this;
        this.project_duration = [];
        
        _.each(projects, function(project, index) {
            if (this.date_stop && project[this.date_stop]) {
                //ToDO
                console.log('TODO for date_stop');
                self.project_duration.push(0);
            } else if(self.date_delay && project[self.date_delay]) {
                self.project_duration.push(project[self.date_delay]);
            } else {
                self.project_duration.push(0);
            }
        });
        
        this.max_project_duration = _.max(this.project_duration);
        
        return $.Deferred().resolve().promise();
    },
    
    calculate_difference: function() {
        
        
        var extend_end_date_day = Math.floor(this.max_project_duration / this.day_length),
            extend_end_date_hours = this.max_project_duration % this.day_length;
        
        this.project_end_date = this.project_end_date.add({days: extend_end_date_day, hours: extend_end_date_hours})
        
        var DAY = 1000 * 60 * 60 * 24,
            difference = Math.abs(this.project_start_date.getTime() - this.project_end_date.getTime()),
            day = Math.ceil(difference / DAY),
            hour = (difference % DAY)/(1000 * 60 * 60),
            DiffHour = (day * this.day_length) + hour;
            
        this.total_duration = parseFloat(DiffHour.toFixed(2));
        return $.Deferred().resolve().promise();
    },
    
    add_tasks: function(tasks, parentTask) {
        var self = this;
        
        _.each(tasks, function(task, index) {
            parentTask.addChildTask(new GanttTaskInfo(task.id, task.name, self.format_date(task[self.date_start]), self.project_duration[index], 100, ""));
        });
        
        return $.Deferred().resolve().promise();
    },
    
    project_starting_date : function(projects) {
        var self = this;
        var min_date = _.min(projects, function(prj) {
            return new Date(prj[self.date_start]);
        });
        
        var max_date = _.max(projects, function(prj) {
            return self.format_date(prj[self.date_start])
        });
        this.project_end_date =  this.format_date(max_date[self.date_start]);
        if (min_date) this.project_start_date = this.format_date(min_date[self.date_start]);
        else 
            this.project_start_date = Date.today();
        
        return $.Deferred().resolve().promise();
    },

    init_gantt_view: function(Project, Task) {
        
        Project.addTask(Task);
        var self = this,
            ganttChartControl = new GanttChart();

        // Setup paths and behavior
        ganttChartControl.setImagePath("/web_gantt/static/lib/dhtmlxGantt/codebase/imgs/");
        ganttChartControl.setEditable(true);
        ganttChartControl.showTreePanel(true);
        ganttChartControl.showContextMenu(false);
        ganttChartControl.showDescTask(true,'d,s-f');
        ganttChartControl.showDescProject(true,'n,d');
        // Load data structure      
        ganttChartControl.addProject(Project);
        ganttChartControl.create('GanttView');
        // Create Gantt control
        
        
        // Setup Events
        ganttChartControl.attachEvent("onTaskStartDrag", function(task) {
            var task_date = task.getEST();
            if(task_date.getHours()) {
                task_date.set({hour: task_date.getHours(), minute : task_date.getMinutes(), second:0});
            }
        });
        ganttChartControl.attachEvent("onTaskEndResize", function(task) {return self.ResizeTask(task);});
        ganttChartControl.attachEvent("onTaskEndDrag", function(task) {return self.ResizeTask(task);});
        
        ganttChartControl.attachEvent("onTaskDblClick", function(task) { return self.editTask(task);});
        
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
        return openerp.web.auto_str_to_date(date);
    },
    
    ResizeTask: function(task) {
        
        var event_id = task.getId();
        
        
        if(!event_id)
            return this.do_warn(_t("Project can not be resized"));
            
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
                self.reloadView();
            });
    },
    
    editTask: function(task) {
        var self = this;
        var event_id = task.getId();
        if(!event_id)
            return false;
            
        if(event_id) event_id = parseInt(event_id, 10);
        
        var action_manager = new openerp.web.ActionManager(this);
        
        var dialog = new openerp.web.Dialog(this, {
            width: 800,
            height: 600,
            buttons : {
                Cancel : function() {
                    $(this).dialog('destroy');
                },
                Save : function() {
                    var form_view = action_manager.inner_viewmanager.views.form.controller;

                    form_view.do_save(function() {
                        self.reloadView();
                    });
                    $(this).dialog('destroy');
                }
            }
        }).start().open();
        action_manager.appendTo(dialog.$element);
        action_manager.do_action({
            res_model : this.dataset.model,
            res_id: event_id,
            views : [[false, 'form']],
            type : 'ir.actions.act_window',
            auto_search : false,
            flags : {
                search_view: false,
                sidebar : false,
                views_switcher : false,
                action_buttons : false,
                pager: false
            }
        });
    },
    
    reloadView: function() {
       self.on_project_loaded(self.database_projects);
    },

    do_show: function () {
        this.$element.show();
    },

    do_hide: function () {
        this.$element.hide();
    },

    do_search: function (domains, contexts, groupbys) {
        var self = this;
        this.group_by = groupbys;
        $.when(this.has_been_loaded).then(function() {
            self.dataset
                .read_slice([], {
                    domain: domains,
                    context: contexts,
                    group_by: groupbys
                })
                .done(function(projects) {
                    self.database_projects = projects; 
                    self.on_project_loaded(projects);
                });
        })
        
    }

});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};
// vim:et fdc=0 fdl=0:
