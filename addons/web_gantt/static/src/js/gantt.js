/*---------------------------------------------------------
 * OpenERP web_gantt
 *---------------------------------------------------------*/
openerp.web_gantt = function (openerp) {
var QWeb = openerp.web.qweb;
QWeb.add_template('/web_gantt/static/src/xml/web_gantt.xml');
openerp.web.views.add('gantt', 'openerp.web_gantt.GanttView');
openerp.web_gantt.GanttView = openerp.web.View.extend({

init: function(parent, element_id, dataset, view_id) {
        this._super(parent, element_id);
        this.view_manager = parent || new openerp.web.NullViewManager();
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
        this.colors = [];
        this.color_values = [];
        this.calendar_fields = {};
        this.info_fields = [];
        this.domain = this.dataset._domain ? this.dataset._domain: [];
        this.context = this.dataset.context || {};
    },

    start: function() {
        this._super();
        this.rpc("/web/view/load", {"model": this.model, "view_id": this.view_id, "view_type": "gantt"}, this.on_loaded);
    },

    on_loaded: function(data) {

        var self = this;
        this.fields_view = data;

        this.name =  this.fields_view.arch.attrs.string;
        this.view_id = this.fields_view.view_id;

        this.date_start = this.fields_view.arch.attrs.date_start;
        this.date_delay = this.fields_view.arch.attrs.date_delay;
        this.date_stop = this.fields_view.arch.attrs.date_stop;

        this.color_field = this.fields_view.arch.attrs.color;
        this.day_length = this.fields_view.arch.attrs.day_length || 8;
        this.colors = this.fields_view.arch.attrs.colors;
        var arch_children = this.fields_view.arch.children[0];
        this.text = arch_children.children[0] ? arch_children.children[0].attrs.name : arch_children.attrs.name;
        this.parent = this.fields_view.arch.children[0].attrs.link;

        this.format = "yyyy-MM-dd";
        this.grp = [];

        self.create_gantt();
        self.get_events();

        this.$element.html(QWeb.render("GanttView", {"view": this, "fields_view": this.fields_view}));

    },

    create_gantt: function() {

        ganttChartControl = new GanttChart(this.day_length);
        ganttChartControl.setImagePath("/web_gantt/static/lib/dhtmlxGantt/codebase/imgs/");
        ganttChartControl.setEditable(true);
        ganttChartControl.showTreePanel(true);
        ganttChartControl.showContextMenu(true);
        ganttChartControl.showDescTask(true,'d,s-f');
        ganttChartControl.showDescProject(true,'n,d');

    },

    get_events: function() {

        var self = this;
        this.dataset.read_slice([],{}, function(result) {
            self.load_event(result);
        });

    },

    load_event: function(events) {

        var self = this;
        var result = events;
        var smalldate = "";

        COLOR_PALETTE = ['#ccccff', '#cc99ff', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
                 '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
                 '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
                 '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900'];

        if (result.length != 0){
            var show_event = [];
            for (var i in result){
                var res = result[i];
                if (res[this.date_start] != false){
                    
                    var start_date = this.convert_str_date(res[this.date_start]);
                    res[this.date_start] = start_date;
                    show_event.push(res);
                    if (smalldate == ""){
                        smalldate = start_date;
                    }
                    else{
                        if (start_date < smalldate){
                            smalldate = start_date;
                        }
                    }
                }
            }
            if (smalldate == ""){
                smalldate = Date.today();
            }
            project = new GanttProjectInfo("_1", "", smalldate);
            ganttChartControl.addProject(project);
        }

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

            var color = res[this.color_field][0] || res[this.color_field];
            if (color_box[color] == undefined){
                color_box[color] = COLOR_PALETTE[k];
                k += 1;
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
            if (!duration)
                duration = 0;

            if (self.grp.length){
                for (var j in self.grp){
                    var grp_key = res[self.grp[j]['group_by']];
                    if (typeof(grp_key) == "object"){
                        grp_key = res[self.grp[j]['group_by']][1];
                    }
                    else{
                        grp_key = res[self.grp[j]['group_by']];
                    }

                    if (!grp_key){
                        grp_key = "Undefined";
                    }

                    if (j == 0){
                        if (parents[grp_key] == undefined){
                            var mod_id = i+ "_" +j;
                            parents[grp_key] = mod_id;
                            child_event[mod_id] = {};
                            all_events[mod_id] = {'parent': "", 'evt':[mod_id , grp_key, start_date, start_date, 100, "", "white"]};
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
                            all_events[ch_mod_id] = {'parent': mod_id, 'evt':[ch_mod_id , grp_key, start_date, start_date, 100, "","white"]};
                            mod_id = ch_mod_id;
                        }
                        else{
                            mod_id = child_event[mod_id][grp_key];
                            temp_id = mod_id;
                        }
                    }
                }
                all_events[id] = {'parent': temp_id, 'evt':[id , text, start_date, duration, 100, "", color_box[color]]};
                final_events.push(id);
            }
            else {
                if (i == 0) {
                    var mod_id = "_" + i;
                    all_events[mod_id] = {'parent': "", 'evt': [mod_id, this.name, start_date, start_date, 100, "", "white"]};
                }
                all_events[id] = {'parent': mod_id, 'evt':[id , text, start_date, duration, 100, "", color_box[color]]};
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

        for (var j in self.grp) {
            self.render_events(all_events, j);
        }

        if (!self.grp.length) {
            self.render_events(all_events, 0);
        }

        for (var i in final_events){
            evt_id = final_events[i];
            res = all_events[evt_id];
            task=new GanttTaskInfo(res['evt'][0], res['evt'][1], res['evt'][2], res['evt'][3], res['evt'][4], "",res['evt'][6]);
            prt = project.getTaskById(res['parent']);
            prt.addChildTask(task);
        }

        var oth_hgt = 264;
        var min_hgt = 150;
        var name_min_wdt = 150;
        var gantt_hgt = jQuery(window).height() - oth_hgt;
        var search_wdt = jQuery("#oe_app_search").width();

        if (gantt_hgt > min_hgt){
            jQuery('#GanttDiv').height(gantt_hgt).width(search_wdt);
        } else{
            jQuery('#GanttDiv').height(min_hgt).width(search_wdt);
        }

        ganttChartControl.create("GanttDiv");
        ganttChartControl.attachEvent("onTaskStartDrag", function(task) {self.on_drag_start(task);});
        ganttChartControl.attachEvent("onTaskEndResize", function(task) {self.on_resize_drag_end(task, "resize");});
        ganttChartControl.attachEvent("onTaskEndDrag", function(task) {self.on_resize_drag_end(task, "drag");});
        ganttChartControl.attachEvent("onTaskDblClick", function(task) {self.open_popup(task);});

        var taskdiv = jQuery("div.taskPanel").parent();
        taskdiv.addClass('ganttTaskPanel');
        taskdiv.prev().addClass('ganttDayPanel');
        var $gantt_panel = jQuery(".ganttTaskPanel , .ganttDayPanel");

        var ganttrow = jQuery('.taskPanel').closest('tr');
        var gtd =  ganttrow.children(':first-child');
        gtd.children().addClass('task-name');

        jQuery(".toggle-sidebar").click(function(e) {
            self.set_width();
        });

        jQuery(window).bind('resize',function(){
            window.clearTimeout(ganttChartControl._resize_timer);
            ganttChartControl._resize_timer = window.setTimeout(function(){
                self.reload_gantt();
            }, 200);
        });

        jQuery("div #_1, div #_1 + div").hide();
    },

    set_width: function() {

        $gantt_panel.width(1);
        jQuery(".ganttTaskPanel").parent().width(1);

        var search_wdt = jQuery("#oe_app_search").width();
        var day_wdt = jQuery(".ganttDayPanel").children().children().width();
        jQuery('#GanttDiv').css('width','100%');

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
                        task = new GanttTaskInfo(res['evt'][0], res['evt'][1], res['evt'][2], res['evt'][3], res['evt'][4], "",res['evt'][6]);
                        project.addTask(task);
                    } else {
                        task = new GanttTaskInfo(res['evt'][0], res['evt'][1], res['evt'][2], res['evt'][3], res['evt'][4], "",res['evt'][6]);
                        prt = project.getTaskById(res['parent']);
                        prt.addChildTask(task);
                    }
                }
            }
        }
    },

    open_popup : function(task) {
        var event_id = task.getId();
        if(event_id.toString().search("_") != -1)
            return;
        if(event_id) event_id = parseInt(event_id, 10);

        var action = {
            "res_model": this.dataset.model,
            "res_id": event_id,
            "views":[[false,"form"]],
            "type":"ir.actions.act_window",
            "view_type":"form",
            "view_mode":"form"
        };

        action.flags = {
            search_view: false,
            sidebar : false,
            views_switcher : false,
            pager: false
        };
        var element_id = _.uniqueId("act_window_dialog");
        var dialog = jQuery('<div>', {
            'id': element_id
            }).dialog({
                modal: true,
                width: 'auto',
                height: 'auto',
                buttons: {
                    Cancel: function() {
                        $(this).dialog("destroy");
                    },
                    Save: function() {
                        var view_manager = action_manager.viewmanager;
                        var _dialog = this;
                        view_manager.views[view_manager.active_view].controller.do_save(function(r) {
                            $(_dialog).dialog("destroy");
                            self.reload_gantt();
                        })
                    }
                }
        });
        var action_manager = new openerp.web.ActionManager(this, element_id);
        action_manager.start();
        action_manager.do_action(action);

        //Default_get
        if(!event_id) action_manager.viewmanager.dataset.index = null;
    },

    on_drag_start : function(task){
        var st_date = task.getEST();
        if(st_date.getHours()){
            self.hh = st_date.getHours();
            self.mm = st_date.getMinutes();
        }
    },

    on_resize_drag_end : function(task, evt){

        var event_id = task.getId();
        var data = {};

        if(event_id.toString().search("_") != -1)
            return;
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
        this.dataset.write(event_id, data, {}, function(result) {});

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
            return openerp.web.str_to_datetime(str);
        } else if (str.length == 10){
            this.format = "yyyy-MM-dd";
            return openerp.web.str_to_date(str);
        } else if (str.length == 8){
            this.format = "HH:mm:ss";
            return openerp.web.str_to_time(str);
        }
        throw "Unrecognized date/time format";
    },

    convert_date_str: function(full_date) {
        if (this.format == "yyyy-MM-dd HH:mm:ss"){
            return openerp.web.datetime_to_str(full_date);
        } else if (this.format == "yyyy-MM-dd"){
            return openerp.web.date_to_str(full_date);
        } else if (this.format == "HH:mm:ss"){
            return openerp.web.time_to_str(full_date);
        }
        throw "Unrecognized date/time format";
    },

    reload_gantt: function() {
        var self = this;
        this.dataset.read_slice([],{}, function(response) {
            ganttChartControl.clearAll();
            jQuery("#GanttDiv").children().remove();
            self.load_event(response);
        });
    },

    do_search: function (domains, contexts, groupbys) {
        var self = this;
        this.grp = groupbys;
        return this.rpc('/web/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            self.reload_gantt();
        });
    }

});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};
// vim:et fdc=0 fdl=0:
