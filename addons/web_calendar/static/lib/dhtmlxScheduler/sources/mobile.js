/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
if (!window.scheduler){
	window.scheduler = {	
		config:{
 		},
 		templates:{
 		},
		xy:{
		},
		locale:{
		}
	};
}
/*Locale*/
if(!scheduler.locale)
   scheduler.locale = {};
scheduler.locale.labels = {
	list_tab : "List",
	day_tab : "Day",
	month_tab : "Month",
	icon_today : "Today",
	icon_save : "Save",
	icon_delete : "Delete event",
	icon_cancel : "Cancel",
	icon_edit : "Edit",
	icon_back : "Back",
	icon_close : "Close form",
	icon_yes : "Yes",
	icon_no : "No",
	confirm_closing : "Your changes will be lost, are your sure ?",
	confirm_deleting : "Event will be deleted permanently, are you sure?",
	label_event:"Event",
	label_start:"Start",
	label_end:"End",
	label_details:"Notes",
	label_from: "from",
	label_to: "to"
};

/*Config*/

/*date*/

scheduler.config = {
	init_date : new Date(),
	form_date : "%d-%m-%Y %H:%i",
	xml_date : "%Y-%m-%d %H:%i",
	item_date : "%d.%m.%Y",
	header_date : "%d.%m.%Y",
	hour_date : "%H:%i",
	scale_hour : "%H",
	calendar_date : "%F %Y"
};

scheduler.config.form_rules = {
	end_date:function(value,obj){
		return (obj.start_date.valueOf() < value.valueOf());
	}
};

/*Dimentions*/
scheduler.xy = {
   	confirm_height : 231,
	confirm_width : 250,
	scale_width : 45,
	scale_height : 15,
	list_tab:54,
	day_tab:54,
	month_tab:68,
	icon_today : 72,
	icon_save : 100,
	icon_cancel : 100,
	icon_edit : 100,
	icon_back : 100,
	list_height: 42,
	month_list_height: 42
}

/*Templates*/
scheduler.templates = {
	selected_event : function(obj){
		var html = "";
		if(!obj.start_date) return html;
		html += "<div  class='selected_event'>";
		html += "<div class='event_title'>"+obj.text+"</div>";
		if(dhx.Date.datePart(obj.start_date).valueOf()==dhx.Date.datePart(obj.end_date).valueOf()){
			var fd = dhx.i18n.dateFormatStr(obj.start_date);
			var fts = dhx.i18n.timeFormatStr(obj.start_date);
			var fte = dhx.i18n.timeFormatStr(obj.end_date);
			html += "<div class='event_text'>"+fd+"</div>";
			html += "<div class='event_text'>"+scheduler.locale.labels.label_from+" "+fts+" "+scheduler.locale.labels.label_to+" "+fte+"</div>";
		}
		else{
			var fds = dhx.i18n.longDateFormatStr(obj.start_date);
			var fde = dhx.i18n.longDateFormatStr(obj.end_date);
			var fts = dhx.i18n.timeFormatStr(obj.start_date);
			var fte = dhx.i18n.timeFormatStr(obj.end_date);
			html += "<div class='event_text'>"+scheduler.locale.labels.label_from+" "+fts+" "+fds+"</div>";
			html += "<div class='event_text'>"+scheduler.locale.labels.label_to+" "+fte+" "+fde+"</div>";
		}
		if(obj.details&&obj.details!==""){
			html += "<div class='event_title'>"+scheduler.locale.labels.label_details+"</div>";
			html += "<div class='event_text'>"+obj.details+"</div>";
		}
		html += "</div>";
		return html;
	},
	calendar_event : function(date){
		return date+"<div class='day_with_events'></div>";
	},
	event_date: function(date){
		return dhx.i18n.dateFormatStr(date);
	},
	event_long_date: function(date){
		return dhx.i18n.longDateFormatStr(date);
	},
	event_time : function(date){
		return dhx.i18n.timeFormatStr(date);
	},
	event_color : function(obj,type){
		return (obj.color?"background-color:"+obj.color:"");
	},
	event_marker : function(obj,type){
   		return "<div class='dhx_event_marker' style='"+type.color(obj)+"'></div>";
	},
	event_title: function(obj,type){
		return "<div class='dhx_day_title'>"+type.dateStart(obj.start_date)+"</div><div style='margin:10px'><div class='dhx_event_time'>"+type.timeStart(obj.start_date)+"</div>"+type.marker(obj,type)+"<div class='dhx_event_text'>"+obj.text+"</div></div>";
	},
	month_event_title : function(obj,type){
		return type.marker(obj,type)+"<div class='dhx_event_time'>"+type.timeStart(obj.start_date)+"</div><div class='dhx_event_text'>"+obj.text+"</div>"	
	},
	day_event: function(obj,type){
		return obj.text	
	}
};

/*Views of scheduler multiview*/
scheduler.config.views = [];


dhx.ready(function(){
	if (scheduler.locale&&scheduler.locale.date)
		dhx.Date.Locale = scheduler.locale.date;

	if(!scheduler.config.form){
		scheduler.config.form = [
			{view:"text",		label:scheduler.locale.labels.label_event,	name:'text'},
			{view:"datepicker",	label:scheduler.locale.labels.label_start,	name:'start_date',	timeSelect:1, dateFormat:scheduler.config.form_date},
			{view:"datepicker",	label:scheduler.locale.labels.label_end,	name:'end_date',	timeSelect:1, dateFormat:scheduler.config.form_date},
			{view:"textarea",	label:scheduler.locale.labels.label_details,	name:'details',		width:300, height:150},
			{view:"button",		label:scheduler.locale.labels.icon_delete,	id:'delete',type:"form" ,css:"delete"}
		];
	}
	if(!scheduler.config.bottom_toolbar){
		scheduler.config.bottom_toolbar = [
 			{ view:"button",id:"today",label:scheduler.locale.labels.icon_today,inputWidth:scheduler.xy.icon_today, align:"left",width:scheduler.xy.icon_today+6},
 			{ view:"segmented", id:"buttons",selected:"list",align:"center",multiview:true, options:[
				{value:"list", label:scheduler.locale.labels.list_tab,width:scheduler.xy.list_tab},
				{value:"day", label:scheduler.locale.labels.day_tab,width:scheduler.xy.day_tab},
    			{value:"month", label:scheduler.locale.labels.month_tab,width:scheduler.xy.month_tab}
			]},
			{ view:"button",css:"add",id:"add", align:"right",label:"",inputWidth:42,width:50},
			{ view:"label", label:"",inputWidth:42,width:50, batch:"readonly"}
		];
	}
	if(!scheduler.config.day_toolbar){
		scheduler.config.day_toolbar = [
			{view:'label',id:"prev",align:"left",label:"<div class='dhx_cal_prev_button'><div></div></div>"},
			{view:'label',id:"date",align:"center",width:200},
			{view:'label',id:"next",align:"right",label:"<div class='dhx_cal_next_button'><div></div></div>"}
		];
	}
	if(!scheduler.config.selected_toolbar){
		scheduler.config.selected_toolbar = [
			{view:'button', inputWidth:scheduler.xy.icon_back, type:"prev", id:"back",align:"left",label:scheduler.locale.labels.icon_back},
			{view:'button', inputWidth:scheduler.xy.icon_edit, id:"edit",align:"right",label:scheduler.locale.labels.icon_edit}
		];
	}
	if(!scheduler.config.form_toolbar){
		scheduler.config.form_toolbar = [
			{view:'button', inputWidth:scheduler.xy.icon_cancel, id:"cancel",css:"cancel",align:"left",label:scheduler.locale.labels.icon_cancel},
			{view:'button', inputWidth:scheduler.xy.icon_save, id:"save",align:"right",label:scheduler.locale.labels.icon_save}
		];
	}
	
	/*List types*/
	scheduler.types = {
		event_list:{
			name:"EventsList",
			css:"events",
			cssNoEvents:"no_events",
			padding:0,
			height:scheduler.xy.list_height,
			width:"auto",
			dateStart:scheduler.templates.event_date,
			timeStart:scheduler.templates.event_time,
			color:scheduler.templates.event_color,
			marker:scheduler.templates.event_marker, 
			template:scheduler.templates.event_title
		},
		day_event_list:{
			name:"DayEventsList",
			css:"day_events",
			cssNoEvents:"no_events",
			padding:0,
			height:scheduler.xy.month_list_height,
			width:"auto",
			timeStart:scheduler.templates.event_time,
			color:scheduler.templates.event_color,
			marker:scheduler.templates.event_marker, 
			template:scheduler.templates.month_event_title
		}
	};
		
	dhx.Type(dhx.ui.list, scheduler.types.event_list);
	dhx.Type(dhx.ui.list, scheduler.types.day_event_list);

	dhx.DataDriver.scheduler = {
	    records:"/*/event"
	};
	dhx.extend(dhx.DataDriver.scheduler,dhx.DataDriver.xml);
    
	/*the views of scheduler multiview*/
	var views = [
		{
			id:"list",
			view:"list",
			type:"EventsList",
			startDate:new Date()
		},
		{
			id:"day",
			rows:[
				{	
					id:"dayBar",
					view:"toolbar",
					css:"dhx_topbar",
					elements: scheduler.config.day_toolbar
				},
				{
					id:"dayList",
					view:"dayevents"
				}
			]
		},
		{
			id:"month",
			rows:[
				{
					id:"calendar",
					view:"calendar",
					dayWithEvents: scheduler.templates.calendar_event,
					calendarHeader:scheduler.config.calendar_date
				},
				{
					id:"calendarDayEvents",
					view:"list",
					type:"DayEventsList"
				}
			]
			
		},
		{
			id:"event",
			animate:{
				type:"slide",
				subtype:"in",
				direction:"top"
			},
			rows:[
				{
					id:"eventBar",
					view:"toolbar",
					type:"TopBar",
					css:"single_event",
					elements: scheduler.config.selected_toolbar
				},
				{
					id:"eventTemplate",
					view:"template",
					template:scheduler.templates.selected_event
				}
			
			]
		},
		{
			id:"form",
			rows:[
				{	
					id:"editBar",
					view:"toolbar",
					type:"TopBar",
					elements:scheduler.config.form_toolbar 
				},
				{
					id:"editForm",
					view:"form",
					elements: scheduler.config.form,
					rules: scheduler.config.form_rules
				}
			]
		}
	].concat(scheduler.config.views);
	
	dhx.protoUI({
		name:"scheduler",
	    defaults:{
			rows:[
				{
					view:"multiview",
					id:"views",
					cells: views
				},
				{
					view:"toolbar",
					id:"bottomBar",
					type:"SchedulerBar",
					visibleBatch:"default",
					elements: scheduler.config.bottom_toolbar
				}
			],
			color:"#color#",
			textColor:"#textColor#"
		},
		$init: function() {
	    	this.name = "Scheduler";
			this._viewobj.className += " dhx_scheduler";
			/*date format functions*/
			dhx.i18n.dateFormat = scheduler.config.item_date;
    		dhx.i18n.timeFormat = scheduler.config.hour_date;
 		    dhx.i18n.fullDateFormat = scheduler.config.xml_date;
			dhx.i18n.headerFormatStr = dhx.Date.dateToStr( scheduler.config.header_date);
			dhx.i18n.setLocale();
			this.data.provideApi(this);
			this.data.extraParser = dhx.bind(function(data){
				data.start_date	= dhx.i18n.fullDateFormatDate(data.start_date);
				data.end_date 	= dhx.i18n.fullDateFormatDate(data.end_date);
			},this);
			this.$ready.push(this._initStructure);
			this.data.attachEvent("onStoreUpdated", dhx.bind(this._sortDates,this));
	    },
	    _initStructure:function(){
			this._initToolbars();
			this._initmonth();
			
			//store current date
			this.coreData = new dhx.DataValue();
			this.coreData.setValue(scheduler.config.init_date);
			
			this.$$("dayList").define("date",this.coreData);
			
			this.selectedEvent = new dhx.DataRecord();
			
			if(this.config.readonly){
				this.define("readonly",this.config.readonly);
			}
			else if(scheduler.config.readonly)
				this.define("readonly",true);
			/*saving data*/
			if(this.config.save){
				var dp = new dhx.DataProcessor({
					master:this,
					url:this.config.save
				});
				dp.attachEvent("onBeforeDataSend",this._onSchedulerUpdate);
			}
				
			if(this.$$("date"))
				this.$$("date").bind(this.coreData, null, dhx.i18n.headerFormatStr);
			
			
			this.$$("list").sync(this);
			this.$$("list").bind(this.coreData, function(target, source){
				return source < target.end_date;
			});
			
			this.$$("dayList").sync(this, true);
			this.$$("dayList").bind(this.coreData, function(target, source){
				var d = dhx.Date.datePart(source);
				return d < target.end_date && dhx.Date.add(d,1,"day") > target.start_date;
			});
			
			this.$$("calendar").bind(this.coreData);
			
			this.$$("calendarDayEvents").sync(this, true);
			this.$$("calendarDayEvents").bind(this.coreData, function(target, source){
				var d = dhx.Date.datePart(source);
				return d < target.end_date && dhx.Date.add(d,1,"day") > target.start_date;
			});
			
			this.$$("eventTemplate").bind(this);
			this.$$("editForm").bind(this);
			
			this.$$("list").attachEvent("onItemClick", dhx.bind(this._on_event_clicked, this));
			this.$$("dayList").attachEvent("onItemClick", dhx.bind(this._on_event_clicked, this));
			this.$$("calendarDayEvents").attachEvent("onItemClick", dhx.bind(this._on_event_clicked, this));
		},
		_on_event_clicked:function(id){
			this.setCursor(id);
			this.$$('event').show();
		},
		/*Sorts dates asc, gets hash of dates with event*/
		_sortDates:function(){
			this.data.blockEvent();
			this.data.sort(function(a,b){
				return a.start_date < b.start_date?1:-1;
			});
			this.data.unblockEvent();
			this._eventsByDate = {};
			var evs = this.data.getRange();
			for(var i = 0; i < evs.length;i++)
				this._setDateEvents(evs[i]);
		},
		/*Month Events view: gets dates of a certain event*/
		_setDateEvents:function(ev){
			var start = dhx.Date.datePart(ev.start_date);
			var end = dhx.Date.datePart(ev.end_date);
			if(ev.end_date.valueOf()!=end.valueOf())
				end = dhx.Date.add(end,1,"day");
			while(start<end){
			    this._eventsByDate[start.valueOf()]=true;
				start = dhx.Date.add(start,1,"day");
			}
		},
		/* Month Events view: sets event handlers */
		_initmonth:function(){
			this.$$("calendar").attachEvent("onDateSelect",dhx.bind(function(date){
				this.setDate(date);
			},this));
			
			this.$$("calendar").attachEvent("onAfterMonthChange",dhx.bind(function(date){
				var today = new Date();
				if(date.getMonth()===today.getMonth()&&date.getYear()===today.getYear())
					date = today;
				else
					date.setDate(1);
				this.setDate(date);
			},this));
			
			var dayFormat = this.$$("calendar").config.calendarDay;
			this.$$("calendar").config.calendarDay=dhx.bind(function(date){
				var html = dayFormat(date);
				if(this._eventsByDate&&this._eventsByDate[date.valueOf()])
					return this.$$("calendar").config.dayWithEvents(html);
				return html;
			},this);
		},

		/*applies selected date to all lists*/
		setDate:function(date, inc, mode){
			if (!date)
				date = this.coreData.getValue();
			if (inc)
				date = dhx.Date.add(date, inc, mode);
			this.coreData.setValue(date);
		},
		_initToolbars:function(){
			this.attachEvent("onItemClick", function(id){
				var view_id = this.innerId(id);
				switch(view_id){
					case "today":
						this.setDate(new Date());	
						break;
					case "add":
						if(this.innerId(this.$$("views").getActive()) == "form"){
							var self = this;
							dhx.confirm({
								height:scheduler.xy.confirm_height,
								width:scheduler.xy.confirm_width,
								title: scheduler.locale.labels.icon_close,
								message: scheduler.locale.labels.confirm_closing,
								callback: function(result) {
									if (result){
										self._addEvent();
									}
								},
								labelOk:scheduler.locale.labels.icon_yes,
								labelCancel:scheduler.locale.labels.icon_no,
								css:"confirm"
				
							});
						}else{
							this._addEvent();
						}
						break;
					case "prev":
						this.setDate(null, -1, "day");
						break;
			    	case "next":
			    		this.setDate(null, 1, "day");
			    		break;
			    	case "edit":
					    if(this.$$("delete"))
							this.$$("delete").show();
						this.define("editEvent",true);
						this.$$("form").show();
						break;
					case "back":
						this.$$("views").back();
						break;
					case "cancel":
						/*if(!this._settings.editEvent)
							this.remove(this.getCursor());*/
						this.callEvent("onAfterCursorChange",[this.getCursor()]);
						this.$$("views").back();
						break;
					case "save":
						if(this.$$("editForm").validate()){
							if(!this._settings.editEvent){
								var data = this.$$("editForm").getValues();
								data.id = dhx.uid();
								this.add(data);
								this.setCursor(data.id);
							} else {
								this.$$("editForm").save();
							}
							dhx.dp(this).save();
							this.setDate();
							this.$$("views").back();
						}
						break;
					case "delete":
						this._deleteEvent();
						break;
					default:
						//do nothing
						break;
				}		
			});
			this.attachEvent("onAfterTabClick", function(id, button){
				this.$$(button).show();
			});
			this.attachEvent("onBeforeTabClick", function(id, button){
				return this._confirmViewChange(button);
			});
		},
		readonly_setter:function(val){
			if(this.$$("add")){
			if (val){
					this.$$("bottomBar").showBatch("readonly");
					this.$$("add").hide();
					this.$$("edit").hide();
				}
				else{
					this.$$("bottomBar").showBatch("default");
					this.$$("add").show();
					this.$$("edit").show();
				}
			}
			return val;
		},
		/*removes "No events" background*/
		_clearNoEventsStyle:function(){
			if(this.dataCount())
				this._viewobj.className = this._viewobj.className.replace(RegExp(this.type.cssNoEvents, "g"),"");
			else 
				this._viewobj.className += " "+this.type.cssNoEvents;
		},
		/*deletes the cursored event*/
		_deleteEvent: function(){
			var self = this;
			dhx.confirm({
				height:scheduler.xy.confirm_height,
				width:scheduler.xy.confirm_width,
				title: scheduler.locale.labels.icon_delete,
				message: scheduler.locale.labels.confirm_deleting,
				callback: function(result) {
					if (result){
						self.remove(self.getCursor());
						self.$$("views").back(2);
					}
				},
				labelOk:scheduler.locale.labels.icon_yes,
				labelCancel:scheduler.locale.labels.icon_no,
				css:"confirm",
				header:false
			});
		},
		/*adds the new event*/
		_addEvent:function(){
			if(this.$$("delete"))
				this.$$("delete").hide();
			this.define("editEvent",false);				
			this.$$("form").show();
			
			var d = dhx.Date.add(new Date(),1,"hour");
			var start = new Date(d.setMinutes(0));
			var end = dhx.Date.add(start,1,"hour");
			this.$$("editForm").clear();
			this.$$("editForm").setValues({start_date:start,end_date:end});
		},
		/*cofirm the view changing (necessary for edit form)*/
		_confirmViewChange:function(button){
			if(this.innerId(this.$$("views").getActive()) == "form"){
				var self = this;
				if(button!= "today")
					dhx.confirm({
						height:scheduler.xy.confirm_height,
						width:scheduler.xy.confirm_width,
						title: scheduler.locale.labels.icon_close,
						message: scheduler.locale.labels.confirm_closing,
						callback: function(result) {
							if (result){
								self.$$(button).show();
								self.$$("buttons").setValue(button);
							}
						},
						labelOk:scheduler.locale.labels.icon_yes,
						labelCancel:scheduler.locale.labels.icon_no,
						css:"confirm"
					});
				return false;
			}
			return true;
		},
		_onSchedulerUpdate:function(data){
			var obj = data[0].data = dhx.copy(data[0].data);
			obj.start_date = dhx.i18n.fullDateFormatStr(obj.start_date);
			obj.end_date = dhx.i18n.fullDateFormatStr(obj.end_date);
		}
	}, dhx.IdSpace, dhx.DataLoader, dhx.ui.layout, dhx.EventSystem, dhx.Settings);

});
