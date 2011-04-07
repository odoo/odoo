scheduler.attachEvent("onTemplatesReady",function(){
	var s_d = scheduler.date.str_to_date(scheduler.config.api_date);
	var d_s = scheduler.date.date_to_str(scheduler.config.api_date);
	
	var month_x = scheduler.templates.month_day;
	scheduler.templates.month_day=function(date){
		return "<a jump_to='"+d_s(date)+"' href='#'>"+month_x(date)+"</a>";
	}
	var week_x = scheduler.templates.week_scale_date;
	scheduler.templates.week_scale_date=function(date){
		return "<a jump_to='"+d_s(date)+"' href='#'>"+week_x(date)+"</a>";
	}
	
	
	dhtmlxEvent(this._obj,"click",function(e){
		var start = e.target || event.srcElement;
		var to = start.getAttribute("jump_to");
		if (to)
			scheduler.setCurrentView(s_d(to),"day");
	})
})