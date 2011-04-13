/*---------------------------------------------------------
 * OpenERP base_calendar
 *---------------------------------------------------------*/

openerp.base_calendar = function(openerp) {
QWeb.add_template('/base_calendar/static/src/xml/base_calendar.xml');
openerp.base.views.add('calendar', 'openerp.base.CalendarView');
openerp.base.CalendarView = openerp.base.Controller.extend({
// Dhtmlx scheduler ?
	init: function(view_manager, session, element_id, dataset, view_id){
		this._super(session, element_id);
		this.view_manager = view_manager;
        this.dataset = dataset;
        this.dataset_index = 0;
        this.model = dataset.model;
        this.view_id = view_id;
        this.fields_view = {};
        this.widgets = {};
        this.widgets_counter = 0;
        this.fields = this.dataset.fields ? this.dataset.fields: {};
        this.datarecord = {};
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
		this.rpc("/base_calendar/calendarview/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
	},
	on_loaded: function(result) {
		var self = this;
		var params = {};
		this.fields_view = result.fields_view;
		this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
		this.view_id = this.fields_view.view_id;
		
		this.date_start = this.fields_view.arch.attrs.date_start;
		this.date_delay = this.fields_view.arch.attrs.date_delay;
		this.date_stop = this.fields_view.arch.attrs.date_stop;
		
		this.colors = this.fields_view.arch.attrs.colors;
		this.day_length = this.fields_view.arch.attrs.day_length || 8;
		this.color_field = this.fields_view.arch.attrs.color;
		this.fields =  this.fields_view.fields;
		
		//* Calendar Fields *
		this.calendar_fields['date_start'] = {'name': this.date_start, 'kind': this.fields[this.date_start]['type']};
		
		if(this.date_delay)
			this.calendar_fields['date_delay'] = {'name': this.date_delay, 'kind': this.fields[this.date_delay]['type']};
			
		if(this.date_stop)
			this.calendar_fields['date_stop'] = {'name': this.date_stop, 'kind': this.fields[this.date_stop]['type']};
			
		this.calendar_fields['day_length'] = this.day_length;
		//* ------- *
		
		for(var fld=0;fld<this.fields_view.arch.children.length;fld++) {
			this.info_fields.push(this.fields_view.arch.children[fld].attrs.name);
		}
		
		
		this.load_scheduler();
	},
	
	load_scheduler:function() {
		var self = this;
		
		var params = {};
		
		params['model'] = this.model;
		params['calendar_fields'] = this.calendar_fields;
		params['info_fields'] = this.info_fields;
		params['fields'] = this.fields;
		params['color_field'] = this.color_field;
		params['domain'] = this.domain;
		params['colors'] =  this.colors;
		
		/*
		 * Start dhtmlx Schedular
		 */
		scheduler.clearAll();
		scheduler.config.xml_date="%Y-%m-%d %H:%i";
		scheduler.config.multi_day = true; //Multi day events are not rendered in daily and weekly views
		
		this.rpc(
			'/base_calendar/calendarview/schedule_events',
			params,
			function(result) {
				self.schedule_events(result);
			}
		)
	},
	
	schedule_events: function(result) {
		var self = this;
		var res = result.result;
		var sidebar = result.sidebar;
		this.$element.html(QWeb.render("CalendarView", {"view": this, "fields_view": this.fields_view, "sidebar":sidebar, "calendar":this}));
		
		// Initialize Sceduler
		scheduler.init('openerp_scheduler',null,"month");
		scheduler.parse(res,"json");
		jQuery('#dhx_minical_icon').bind('click', this.mini_calendar);
		
		
		// To Change Event
		scheduler.attachEvent(
					'onEventChanged'
					,function(event_id, event_object) {
						self.edit_event(event_id, event_object)
					});
		
		/*
		 * Create Sidebar
		 */
		jQuery('#calendar-sidebar').append(
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
								self.reload_scheduler()
							}),
							sidebar[s][1]
						)
						.css('background-color',sidebar[s][sidebar[s].length-1])
					)
				)
			)
		}
	},
	
	convert_date_format: function(start_date, end_date) {
		var params = {};
		params['start_date'] = start_date.getFullYear() +'-' + start_date.getMonth()+'-' + start_date.getDate()+' '+start_date.getHours()+':'+start_date.getMinutes()+':'+start_date.getSeconds();
		if(end_date) {
			params['end_date'] = end_date.getFullYear() +'-' + end_date.getMonth()+'-' + end_date.getDate()+' '+end_date.getHours()+':'+end_date.getMinutes()+':'+end_date.getSeconds();
		}
		return params; 
	},
	
	edit_event: function(evt_id, evt_object) {
		var dates = this.convert_date_format(evt_object.start_date, evt_object.end_date);
		this.rpc(
			'/base_calendar/calendarview/edit_events',
			{
				'start_date': dates.start_date,
				'end_date': dates.end_date,
				'id': evt_id,
				'model': this.model,
				'info_fields': this.info_fields,
				'fields': this.fields,
				'calendar_fields': this.calendar_fields
			}
		);
	},
	
	mini_calendar: function() {
		
		if(scheduler.isCalendarVisible()) {
			scheduler.destroyCalendar();
		} else {
			scheduler.renderCalendar({
				position:"dhx_minical_icon",
            	date:scheduler._date,
            	navigation:true,
				handler:function(date,calendar){
	               scheduler.setCurrentView(date);
	               scheduler.destroyCalendar()
	            }
			});
		}
	},
	
	reload_scheduler: function() {
//		self.color_field
		console.log('Reload Scheduler>>>')
	},
	
	do_show: function () {
        this.$element.show();
    },
	
    do_hide: function () {
        this.$element.hide();
    }
});

//openerp.base.Action = openerp.base.Action.extend({
//    do_action_window: function(action) {
//        this._super.apply(this,arguments);
//        for(var i = 0; i < action.views.length; i++)  {
//            if(action.views[i][1] == "calendar") {
//                this.calendar_id = action.views[i][0];
//                break;
//            }
//        }
//        // IF there is a view calender
//        // if(this.calendar_id
//    },
//});

};

// DEBUG_RPC:rpc.request:('execute', 'addons-dsh-l10n_us', 1, '*', ('ir.filters', 'get_filters', u'res.partner'))
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
