/*---------------------------------------------------------
 * OpenERP base_gantt
 *---------------------------------------------------------*/

openerp.base_gantt = function (openerp) {
QWeb.add_template('/base_gantt/static/src/xml/base_gantt.xml');
openerp.base.views.add('gantt', 'openerp.base_gantt.GanttView');
openerp.base_gantt.GanttView = openerp.base.Controller.extend({

init: function(view_manager, session, element_id, dataset, view_id) {

        this._super(session, element_id);
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.fields_views = {};
        this.widgets = {};
        this.widgets_counter = 0;
        this.fields = this.dataset.fields ? this.dataset.fields: {};
        this.ids = this.dataset.ids;
        this.name = "";
        this.date_start = "";
        this.date_delay = "";
        this.date_stop = "";
        this.color_field = "";
        this.day_lenth = 8;
        this.colors = [];
        this.color_values = [];
        this.calendar_fields = {};
        this.info_fields = [];
        this.domain = this.dataset._domain ? this.dataset._domain: [];
        this.context = {};
    },

    start: function() {
        this.rpc("/base_gantt/ganttview/load",
        {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },

    on_loaded: function(data) {

        var self = this;
        this.fields_view = data.fields_view;

        this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
        this.view_id = this.fields_view.view_id;

        this.date_start = this.fields_view.arch.attrs.date_start;
        this.date_delay = this.fields_view.arch.attrs.date_delay;
        this.date_stop = this.fields_view.arch.attrs.date_stop;

        this.color_field = this.fields_view.arch.attrs.color;
        this.day_length = this.fields_view.arch.attrs.day_length || 8;
        this.colors = this.fields_view.arch.attrs.colors;

        this.text = this.fields_view.arch.children[0].children[0].attrs.name;
        this.parent = this.fields_view.arch.children[0].attrs.link;

        this.format = "yyyy-MM-dd";

        self.create_gantt();
        self.get_events();

        this.$element.html(QWeb.render("GanttView", {"view": this, "fields_view": this.fields_view}));

    },

    create_gantt: function() {

        ganttChartControl = new GanttChart(this.day_length);
        ganttChartControl.setImagePath("/base_gantt/static/lib/dhtmlxGantt/codebase/imgs/");
        ganttChartControl.setEditable(true);
        ganttChartControl.showTreePanel(true);
        ganttChartControl.showContextMenu(true);
        ganttChartControl.showDescTask(true,'d,s-f');
        ganttChartControl.showDescProject(true,'n,d');

    },

    get_events: function() {

        var self = this;
        this.dataset.read_ids(this.dataset.ids, {}, function(result) {
            self.load_event(result);
        });

    },

    load_event: function(events) {

        var self = this;

        var result = events;
        var project = {};
        var project_smalldate = {};
        var proj_id = [];
        var proj_id_text = [];

        COLOR_PALETTE = ['#ccccff', '#cc99ff', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
                 '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
                 '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
                 '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900']

        //Smallest date of child is parent start date
        for (i in result){
            var res = result[i];

            if (res[this.date_start] != false){

                var parent_id =  res[this.parent][0] || res[this.parent];
                var parent_name = res[this.parent][1];
                var start_date = this.convert_str_date(res[this.date_start]);

                if (project_smalldate[parent_id] == undefined){
                    project_smalldate[parent_id] = start_date;
                    proj_id.push(parent_id);

                    if (parent_name != undefined){
                        proj_id_text.push(res[this.parent]);
                    }
                }
                else{
                    if (start_date < project_smalldate[parent_id]){
                        project_smalldate[parent_id] = start_date;
                    }
                }

            }
        }

        //get parent text
        if (parent_name == undefined){

            var ajax = {
                url: '/base/dataset/call',
                async: false
            };

            this.rpc(ajax, {
                model: this.dataset.model,
                method: "name_get",
                ids: proj_id,
                args: ""
            }, function(response) {
               proj_id_text = response.result;

            });
        }

        //create parents
        for (i in proj_id){

            var id = proj_id_text[i][0];
            var text = proj_id_text[i][1];

            project[id] = new GanttProjectInfo(id, text, project_smalldate[id]);
        }

        //create childs
        var k = 0;
        var color_box = {};
        for (i in result) {

            var res = result[i];
            if (res[this.date_start] != false){

                var parent_id = res[this.parent][0] || res[this.parent];
                var id = res['id'];
                var text = res[this.text];

                var start_date = this.convert_str_date(res[this.date_start]);

                var color = res[this.color_field][0] || res[this.color_field];
                if (color_box[color] == undefined){
                    color_box[color] = COLOR_PALETTE[k];
                    k = k + 1;
                }

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
                if (duration == false)
                    duration = 0
                task = new GanttTaskInfo(id, text, start_date, duration, 100, "", color_box[color]);
                project[parent_id].addTask(task);

            }
        }

        //Add parent
        for (i in proj_id){
            ganttChartControl.addProject(project[proj_id[i]]);
        }

        ganttChartControl.create("GanttDiv");
        ganttChartControl.attachEvent("onTaskStartDrag", function(task) {self.on_drag_start(task);});
        ganttChartControl.attachEvent("onTaskEndResize", function(task) {self.on_resize_drag_end(task, "resize");});
        ganttChartControl.attachEvent("onTaskEndDrag", function(task) {self.on_resize_drag_end(task, "drag");});
        ganttChartControl.attachEvent("onTaskDblClick", function(task) {self.open_popup(task);});

    },

    hours_between: function(date1, date2) {

        var ONE_DAY = 1000 * 60 * 60 * 24;
        var date1_ms = date1.getTime();
        var date2_ms = date2.getTime();
        var difference_ms = Math.abs(date1_ms - date2_ms);

        d = Math.round(difference_ms / ONE_DAY);
        h = Math.round((difference_ms % ONE_DAY)/(1000 * 60 * 60));

        return (d * this.day_length) + h;

    },

    open_popup : function(task) {
        var event_id = task.getId();
        if (event_id) {
            event_id = parseInt(event_id, 10);
            var dataset_event_index = jQuery.inArray(event_id, this.ids);
        } else  {
            var dataset_event_index = null;
        }
        this.dataset.index = dataset_event_index;
        var element_id = _.uniqueId("act_window_dialog");
        var dialog = jQuery('<div>', 
                        {'id': element_id
                    }).dialog({
                        title: 'Gantt Chart',
                        modal: true,
                        minWidth: 800,
                        position: 'top'
                    });
        var event_form = new openerp.base.FormView(this.view_manager, this.session, element_id, this.dataset, false);
        event_form.start();
    },

    on_drag_start : function(task){
        st_date = task.getEST();
        if(st_date.getHours()){
            self.hh = st_date.getHours();
            self.mm = st_date.getMinutes();
        }
    },

    on_resize_drag_end : function(task, evt){

        var event_id = task.getId();
        var data = {};

        if (evt == "drag"){
            full_date = task.getEST().set({hour: self.hh, minute : self.mm, second:0});
            data[this.date_start] = this.convert_date_str(full_date);
        }
        if (this.date_stop != undefined){
            tm = (task.getDuration() % this.day_length);
            stp = task.getFinishDate().add(tm).hour();
            data[this.date_stop] = this.convert_date_str(stp);
        }else{
            data[this.date_delay] = task.getDuration();
        }
        this.dataset.write(event_id, data, function(result) {});

    },

    do_show: function () {
        this.$element.show();
    },

    do_hide: function () {
        this.$element.hide();
    },

    convert_str_date: function (str){
        if (str.length == 19){
            this.format = "yyyy-MM-dd HH:mm:ss";
            return openerp.base.parse_datetime(str);
        } else if (str.length == 10){
            this.format = "yyyy-MM-dd";
            return openerp.base.parse_date(str);
        } else if (str.length == 8){
            this.format = "HH:mm:ss";
            return openerp.base.parse_time(str);
        }
        throw "Unrecognized date/time format";
    },

    convert_date_str: function(full_date) {
        if (this.format == "yyyy-MM-dd HH:mm:ss"){
            return openerp.base.format_datetime(full_date);
        } else if (this.format == "yyyy-MM-dd"){
            return openerp.base.format_date(full_date);
        } else if (this.format == "HH:mm:ss"){
            return openerp.base.format_time(full_date);
        }
        throw "Unrecognized date/time format";
    },

    reload_gantt: function(domain) {
        var self = this;
        var ajax = {
                url: '/base/dataset/search_read',
                async: false
            };
            this.rpc(ajax, {
                model: this.dataset.model,
                domain: self.dataset.domain,
                context :self.dataset.context
            }, function(response) {
                ganttChartControl.clearAll();
                jQuery("#GanttDiv").children().remove();
                self.load_event(response);
            });
    },

    do_search: function (domains, contexts, groupbys) {

        var self = this;

        return this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            return self.reload_gantt(self.dataset.domain);
        });
    }

});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};
// vim:et fdc=0 fdl=0:
