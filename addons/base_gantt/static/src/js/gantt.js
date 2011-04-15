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
        this.fields = {};
        this.datarecord = {};
        this.calendar_fields = {};
    },
    do_show: function () {
        // TODO: re-trigger search
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    start: function() {
        this.rpc("/base_gantt/ganttview/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        var self = this;
        this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
        this.view_id = this.fields_view.view_id;

        this.date_start = this.fields_view.arch.attrs.date_start;
        this.date_delay = this.fields_view.arch.attrs.date_delay;
        this.date_stop = this.fields_view.arch.attrs.date_stop;
        this.color_field = this.fields_view.arch.attrs.color;

        this.day_length = this.fields_view.arch.attrs.day_length || 8;
        this.colors = this.fields_view.arch.attrs.colors;
        this.fields = this.fields_view.fields;

        this.text = this.fields_view.arch.children[0].children[0].attrs.name;
        this.parent = this.fields_view.arch.children[0].attrs.link;

        this.calendar_fields['parent'] = {'name': this.parent};
        this.calendar_fields['date_start'] = {'name': this.date_start};
        this.calendar_fields['text'] = {'name': this.text};
        if(this.date_delay)
            this.calendar_fields['date_delay'] = {'name': this.date_delay};
        if(this.date_stop)
            this.calendar_fields['date_stop'] = {'name': this.date_stop};

        this.calendar_fields['day_length'] = this.day_length;
        this.rpc('/base_gantt/ganttview/get_events',
                {'model': this.model,
                'fields': this.fields,
                'color_field': this.color_field,
                'day_length': this.day_length,
                'calendar_fields': this.calendar_fields,
                'colors': this.colors,
                'info_fields': this.info_fields
                },
                function(res) {
                    self.create_gantt();
                    self.load_event(res);
                })
        this.$element.html(QWeb.render("GanttView", {"view": this, "fields_view": this.fields_view}));

    },
    convert_date_format: function(date) {
        date=date+"";
        if(typeof (date)!="string"||date.length===0){
            return null;
        }
        var iso=date.split("-");
        if(iso.length===0){
            return null;
        }
        var day = iso[2];
        var iso_hours = day.split(' ');

        if (iso_hours.length > 1) {
            day = iso_hours[0];
            var iso_date_hours = iso_hours[1].split(':')
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
    
    create_gantt: function() {
        ganttChartControl = new GanttChart();
        ganttChartControl.setImagePath("/base_gantt/static/lib/dhtmlxGantt/codebase/imgs/");
        ganttChartControl.setEditable(true);
        ganttChartControl.showTreePanel(true);
        ganttChartControl.showContextMenu(true);
        ganttChartControl.showDescTask(true,'d,s-f');
        ganttChartControl.showDescProject(true,'n,d');
    },   
    load_event: function(res) {
        var self = this   
        var result = res.result;
        var sidebar = res.sidebar;
        var project_id = new Array();
        var project = new Array();
        var j = -1;
        var self = this;
        for (i in result) {
        
            var parent_id =  result[i]['parent'][0];
            var parent_name = result[i]['parent'][1];
            
            if (jQuery.inArray(parent_id, project_id) == -1){
                if (parent_id == undefined){
                    parent_name = "";
                }
                j = j + 1;
                project[j] = new GanttProjectInfo(parent_id, parent_name, new Date(2011, 1, 1));
                project_id[j] = parent_id;
            }
            
            var id = result[i]['id'];
            var text = result[i]['text'];
            var start_date = this.convert_date_format(result[i]['start_date']);
            var duration = result[i]['duration'];
            
            var task = new GanttTaskInfo(id, text, start_date, duration, 100, "");
            
            k = project_id.indexOf(parent_id);
            project[k].addTask(task);

        }
        for (i in project_id){
            ganttChartControl.addProject(project[i]);
        }   
        ganttChartControl.create("GanttDiv");
        ganttChartControl.attachEvent("onTaskEndResize", function(task) {self.on_task_end_resize(task);})
        ganttChartControl.attachEvent("onTaskEndDrag", function(task) {self.on_task_end_drag(task);})
        
        //Create Sidebar
        if (jQuery('#cal-sidebar-option').length == 0){
            jQuery('#gantt-sidebar').append(
                jQuery('<table>',{'width':'100%','cellspacing': 0, 'cellpadding': 0, 'id':'cal-sidebar-option'})
            )
            for(s in sidebar) {
                jQuery('#cal-sidebar-option').append(
                    jQuery('<tr>').append(
                        jQuery('<td>').append(
                            jQuery('<div>')
                            .append(
                                jQuery('<input>',
                                {
                                    'type': 'checkbox', 
                                    'id':sidebar[s][0],
                                    'value':sidebar[s][0]
                                }).bind('click',function(){
                                    self.reload_gantt(self.color_field,self.model)
                                }),
                                sidebar[s][1]
                            )
                            .css('background-color',sidebar[s][sidebar[s].length-1])
                        )
                    )
                )
            }
        }
    },
    reload_gantt: function(color_field, model) {
        var domain = [];
        var self = this;
        jQuery('input[type=checkbox]:checked','#cal-sidebar-option').each(function() {
            domain.push(parseInt(jQuery(this).attr('id')))
        });
        this.rpc('/base_gantt/ganttview/reload_gantt',{
            'domain':domain,
            'color_field':color_field,
            'model': model
        },function(res) {
            ganttChartControl.clearAll();
            jQuery("#GanttDiv").children().remove();
            self.load_event(res);
        });
    },
    reverse_convert_date_format: function(date) {
        return date.getFullYear()+"-"+(date.getMonth()+1)+"-"+date.getDate();
    },
    
    on_task_end_resize : function(task) {
        this.rpc('/base_gantt/ganttview/on_event_resize',
                {'id' : task.getId(),
                'end_date' : this.reverse_convert_date_format(task.getFinishDate()),
                'duration' : task.getDuration()
                },
                function(result) {
                })
    },
    on_task_end_drag : function(task) {
        this.rpc('/base_gantt/ganttview/on_event_drag',
                {'id' : task.getId(),
                'start_date' : this.reverse_convert_date_format(task.getEST()),
                'end_date' : this.reverse_convert_date_format(task.getFinishDate()),
                'duration' : task.getDuration()
                },
                function(result) {
                })
    }

});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};

// vim:et fdc=0 fdl=0:
