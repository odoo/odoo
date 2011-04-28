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

        this.format = "%Y-%m-%d";
        this.time = "00:00:00";

        self.create_gantt();
        self.get_events(self.ids);

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

    get_events: function(event_ids) {

        var self = this;
        this.dataset.read_ids(event_ids, {}, function(result) {
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

        //Smallest date of child is parent start date
        for (i in result){
            var res = result[i];

            if (res[this.date_start] != false){

                var parent_id =  res[this.parent][0] || res[this.parent];
                var parent_name = res[this.parent][1];
                var start_date = this.convert_date_format(res[this.date_start]);

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
        for (i in result) {

            var res = result[i];
            if (res[this.date_start] != false){

                var parent_id = res[this.parent][0] || res[this.parent];
                var id = res['id'];
                var text = res[this.text];
                var start_date = this.convert_date_format(res[this.date_start]);

                if (this.date_stop != undefined){
                    if (res[this.date_stop] != false){
                        var stop_date = this.convert_date_format(res[this.date_stop]);
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
                task = new GanttTaskInfo(id, text, start_date, duration, 100, "");
                project[parent_id].addTask(task);

            }
        }

        //Add parent
        for (i in proj_id){
            ganttChartControl.addProject(project[proj_id[i]]);
        }

        ganttChartControl.create("GanttDiv");
        ganttChartControl.attachEvent("onTaskEndResize", function(task) {self.on_resize_drag(task, "resize");})
        ganttChartControl.attachEvent("onTaskEndDrag", function(task) {self.on_resize_drag(task, "drag");})

    },

    hours_between: function(date1, date2) {

        var ONE_DAY = 1000 * 60 * 60 * 24
        var date1_ms = date1.getTime()
        var date2_ms = date2.getTime()
        var difference_ms = Math.abs(date1_ms - date2_ms)

        d = Math.round(difference_ms / ONE_DAY)
        h = Math.round((difference_ms % ONE_DAY)/(1000 * 60 * 60));
        return (d * this.day_length) + h;

    },

    on_resize_drag : function(task, evt) {

        var event_id = task.getId();
        var data = {};

        if (evt == "drag"){
            data[this.date_start] = this.reverse_convert_date_format(task.getEST(), "09:00:00");
        }

        if (this.date_stop != undefined){

            tm = ((task.getDuration() % this.day_length) + 9) + "";
            if (tm.length == 1)
                tm = "0" + tm;

            time = tm + ":00:00";

            data[this.date_stop] = this.reverse_convert_date_format(task.getFinishDate(), time);
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

    convert_date_format: function(date) {

        var self = this;

        if (date.length == 19){
            self.format = "%Y-%m-%d %H:%M:%S";

        }

        date = date+"";
        if(typeof (date) != "string" || date.length === 0){
            return null;
        }
        var iso=date.split("-");
        if(iso.length === 0){
            return null;
        }
        var day = iso[2];

        var iso_hours = day.split(' ');

        if (iso_hours.length > 1) {
            day = iso_hours[0];
            var iso_date_hours = iso_hours[1].split(':');
            var new_date = new Date(iso[0], iso[1] - 1, day);
            new_date.setHours(iso_date_hours[0]);
            new_date.setMinutes(iso_date_hours[1]);
            new_date.setSeconds(iso_date_hours[2]);
        }
        else {
            var new_date = new Date(iso[0], iso[1] - 1, day);
        }

        new_date.setFullYear(iso[0]);
        new_date.setMonth(iso[1]-1);
        new_date.setDate(day);
        return new_date;

    },

    reverse_convert_date_format: function(date, time) {

        var self = this;

        if (self.format == "%Y-%m-%d %H:%M:%S"){
            return date.getFullYear()+'-'+(date.getMonth()+1)+'-'+(date.getDate())+' '+time;
        }
        else{
            return date.getFullYear()+"-"+(date.getMonth()+1)+"-"+date.getDate();
        }

    },

    reload_gantt: function(domain) {

        var self = this;

        this.rpc('/base_gantt/ganttview/reload_gantt',{
            'domain': domain,
            'model': self.model
        },function(event_ids) {
            ganttChartControl.clearAll();
            jQuery("#GanttDiv").children().remove();
            self.get_events(event_ids);
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
