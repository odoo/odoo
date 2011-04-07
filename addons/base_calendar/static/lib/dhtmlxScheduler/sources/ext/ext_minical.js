scheduler.templates.calendar_month =  scheduler.date.date_to_str("%F %Y");
scheduler.templates.calendar_scale_date =  scheduler.date.date_to_str("%D");
scheduler.templates.calendar_date =  scheduler.date.date_to_str("%d");


scheduler.renderCalendar=function(obj, _prev){
	var cal = null;
	var date = obj.date||(new Date());
	if (typeof date == "string")
		date = this.templates.api_date(date);	
		
	if (!_prev){
		var cont = obj.container;
		var pos  = obj.position;
		
		
		if (typeof cont == "string")
			cont = document.getElementById(cont);
	
		if (typeof pos == "string")
			pos = document.getElementById(pos);
		if (pos && (typeof pos.left == "undefined")){
			var tpos = getOffset(pos);
			pos = { 
				top:tpos.top + pos.offsetHeight,
				left:tpos.left
			};
		};
		if (!cont)
			cont = scheduler._get_def_cont(pos);
			
		cal = this._render_calendar(cont,date,obj);
		cal.onclick = function(e){
			e = e||event;
			var src = e.target||e.srcElement;
			
			if (src.className.indexOf("dhx_month_head")!=-1){
				var pname = src.parentNode.className;
				if (pname.indexOf("dhx_after")==-1 && pname.indexOf("dhx_before")==-1) {
					var newdate = scheduler.templates.xml_date(this.getAttribute("date"));
					newdate.setDate(parseInt(src.innerHTML,10));
					scheduler.unmarkCalendar(this);
					scheduler.markCalendar(this,newdate,"dhx_calendar_click");
					this._last_date=newdate;
					if (this.conf.handler) this.conf.handler.call(scheduler, newdate, this);
				}
			}
		};
	} else {
		cal = this._render_calendar(_prev.parentNode, date, obj, _prev);
		scheduler.unmarkCalendar(cal);
	}
		
	
	var start = scheduler.date.month_start(date);
	var end   = scheduler.date.add(start,1,"month");
	var evs = this.getEvents(start,end);
	for (var i=0; i < evs.length; i++){
		var ev = evs[i];
		var d = ev.start_date;
		if (d.valueOf()<start.valueOf()) 
			d = start;
		while (d<=ev.end_date){
			this.markCalendar(cal,d,"dhx_year_event");
			d = this.date.add(d,1,"day");
			if (d.valueOf()>=end.valueOf()) 
				break;
		}
	}
	

	
	cal.conf = obj;
	return cal;
};
scheduler._get_def_cont = function(pos){
	if (!this._def_count){
		this._def_count = document.createElement("DIV");
		this._def_count.style.cssText = "position:absolute;z-index:10100;width:251px; height:175px;";
		this._def_count.onclick = function(e){ (e||event).cancelBubble = true; };
		document.body.appendChild(this._def_count);
	}
		
	this._def_count.style.left = pos.left+"px";
	this._def_count.style.top  = pos.top+"px";
	this._def_count._created = new Date();
	
	return this._def_count;
};
scheduler._locateCalendar=function(cal,date){
	var table=cal.childNodes[2].childNodes[0];
	if (typeof date == "string")
		date = scheduler.templates.api_date(date);
		
	var d  = cal.week_start+date.getDate()-1;
	return table.rows[Math.floor(d/7)].cells[d%7].firstChild;
};
scheduler.markCalendar=function(cal,date,css){
	this._locateCalendar(cal,date).className+=" "+css;
};
scheduler.unmarkCalendar=function(cal,date,css){
	date=date||cal._last_date;
	css=css||"dhx_calendar_click";
	if (!date) return;
	var el = this._locateCalendar(cal,date);
	el.className= (el.className||"").replace(RegExp(css,"g"));
};
scheduler._week_template=function(width){
	var summ = (width || 250);
	var left = 0;

	var week_template = document.createElement("div");
	var dummy_date = this.date.week_start(new Date());
	for (var i=0; i<7; i++){
		this._cols[i]=Math.floor(summ/(7-i));
		this._render_x_header(i,left,dummy_date,week_template);
		dummy_date = this.date.add(dummy_date,1,"day");
		summ-=this._cols[i];
		left+=this._cols[i];
	}
	week_template.lastChild.className+=" dhx_scale_bar_last";
	return week_template;
};
scheduler.updateCalendar=function(obj,sd){
	obj.conf.date = sd;
	this.renderCalendar(obj.conf, obj);
};
scheduler._mini_cal_arrows = ["&nbsp", "&nbsp"];
scheduler._render_calendar=function(obj,sd,conf, previous){
	/*store*/ 
		var ts = scheduler.templates;
		var temp = this._cols; this._cols=[]; 
		var temp2 = this._mode; this._mode = "calendar"; 
		var temp3 = this._colsS; this._colsS = {height:0};
		var temp4 = new Date(this._min_date); 
		var temp5 = new Date(this._max_date); 
		var temp6 = new Date(scheduler._date);
		var temp7 = ts.month_day; ts.month_day=ts.calendar_date;
		
	
	sd = this.date.month_start(sd);
	var week_template = this._week_template(obj.offsetWidth-1);
	
	var d;
	if (previous)
		d = previous;
	else {
		var d = document.createElement("DIV");
		d.className="dhx_cal_container dhx_mini_calendar";
	}
	d.setAttribute("date",this.templates.xml_format(sd));
	d.innerHTML="<div class='dhx_year_month'></div><div class='dhx_year_week'>"+week_template.innerHTML+"</div><div class='dhx_year_body'></div>";
	
	d.childNodes[0].innerHTML=this.templates.calendar_month(sd);
	if (conf.navigation){
	var arrow = document.createElement("DIV");				
		arrow.className = "dhx_cal_prev_button";
		arrow.style.cssText="left:1px;top:2px;position:absolute;";
		arrow.innerHTML = this._mini_cal_arrows[0];
		d.firstChild.appendChild(arrow);
		arrow.onclick=function(){
			scheduler.updateCalendar(d, scheduler.date.add(d._date, -1, "month"));
		};
		
		arrow = document.createElement("DIV");
		arrow.className = "dhx_cal_next_button";
		arrow.style.cssText="left:auto; right:1px;top:2px;position:absolute;";
		arrow.innerHTML = this._mini_cal_arrows[1];
		d.firstChild.appendChild(arrow);
		arrow.onclick=function(){
			scheduler.updateCalendar(d, scheduler.date.add(d._date, 1, "month"));
		};
		d._date = new Date(sd);
	}
	
	d.week_start = (sd.getDay()-(this.config.start_on_monday?1:0)+7)%7;
	
	var dd = this.date.week_start(sd);
	this._reset_month_scale(d.childNodes[2],sd,dd);
	
	var r=d.childNodes[2].firstChild.rows;
	for (var k=r.length; k<6; k++) {
		r[0].parentNode.appendChild(r[0].cloneNode(true));
		for (var ri=0; ri < r[k].childNodes.length; ri++) {
		   r[k].childNodes[ri].className = "dhx_after";
		};
	}
	
	if (!previous)
		obj.appendChild(d);
	
	/*restore*/ this._cols=temp; this._mode = temp2; this._colsS = temp3; this._min_date=temp4; this._max_date=temp5; scheduler._date = temp6; ts.month_day=temp7;
	return d;
};
scheduler.destroyCalendar=function(cal,force){
	if (!cal && this._def_count && this._def_count.firstChild){
		if (force || (new Date()).valueOf() - this._def_count._created.valueOf() > 500)
			cal  = this._def_count.firstChild;
	}
	if (!cal) return;
	cal.onclick=null;
	cal.innerHTML="";
	if (cal.parentNode)
		cal.parentNode.removeChild(cal);
	if (this._def_count)
		this._def_count.style.top = "-1000px";
};
scheduler.isCalendarVisible=function(){
	if (this._def_count && parseInt(this._def_count.style.top,10) > 0 )
		return this._def_count;
	return false;
};
scheduler.attachEvent("onTemplatesReady",function(){
	dhtmlxEvent(document.body, "click", function(){ scheduler.destroyCalendar(); });
});

scheduler.templates.calendar_time = scheduler.date.date_to_str("%d-%m-%Y");

scheduler.form_blocks.calendar_time={
	render:function(){
		var html = "<input class='dhx_readonly' type='text' readonly='true'>";
		
		var cfg = scheduler.config;
		var dt = this.date.date_part(new Date());
		if (cfg.first_hour)
			dt.setHours(cfg.first_hour);
			
		html+=" <select>";
		for (var i=60*cfg.first_hour; i<60*cfg.last_hour; i+=this.config.time_step*1){
			var time=this.templates.time_picker(dt);
			html+="<option value='"+i+"'>"+time+"</option>";
			dt=this.date.add(dt,this.config.time_step,"minute");
		}
		html+="</select>";
		
		var full_day = scheduler.config.full_day;
		
		return "<div style='height:30px; padding-top:0px; font-size:inherit;' class='dhx_cal_lsection dhx_section_time'>"+html+"<span style='font-weight:normal; font-size:10pt;'> &nbsp;&ndash;&nbsp; </span>"+html+"</div>";
	},
	set_value:function(node,value,ev){
	
		var inputs=node.getElementsByTagName("input");	
		var selects=node.getElementsByTagName("select");
		
		var _init_once = function(inp,date,number){
			inp.onclick = function(){
				scheduler.destroyCalendar(null, true);
				scheduler.renderCalendar({
					position:inp, 
					date:new Date(this._date),
					navigation:true,
					handler:function(new_date){
						inp.value = scheduler.templates.calendar_time(new_date);
						inp._date = new Date(new_date);
						scheduler.destroyCalendar();
						if(scheduler.config.event_duration && number == 0) { //first element = start date
							_update_minical_select();
						}
					}
				});
			};
		};	
		
		if(scheduler.config.full_day) {
			if (!node._full_day){
				node.previousSibling.innerHTML+="<div class='dhx_fullday_checkbox'><label><input type='checkbox' name='full_day' value='true'> "+scheduler.locale.labels.full_day+"&nbsp;</label></input></div>";
				node._full_day=true;
			}
			var input=node.previousSibling.getElementsByTagName("input")[0];
			
			var isFulldayEvent = (scheduler.date.time_part(ev.start_date)==0 && scheduler.date.time_part(ev.end_date)==0 && ev.end_date.valueOf()-ev.start_date.valueOf() < 2*24*60*60*1000);
			input.checked = isFulldayEvent;
			for(var i in selects)
				selects[i].disabled=input.checked;			
			for(var i=0; i<inputs.length-1; i++)  //last input = checkbox
				inputs[i].disabled=input.checked;	
				
			input.onclick = function(){ 
				if(input.checked == true) {
					var start_date = new Date(ev.start_date);
					var end_date = new Date(ev.end_date);

					scheduler.date.date_part(start_date);
					end_date = scheduler.date.add(start_date, 1, "day");		
				}
				
				var start = start_date||ev.start_date;
				var end = end_date||ev.end_date;
				_attach_action(inputs[0],start);
				_attach_action(inputs[1],end);
				selects[0].value=start.getHours()*60+start.getMinutes();
				selects[1].value=end.getHours()*60+end.getMinutes();	
				
				for(var i in selects)
					selects[i].disabled=input.checked;
				for(var i=0; i<inputs.length-1; i++)  //last input = checkbox
					inputs[i].disabled=input.checked;	
				
			};
		};
		
		if(scheduler.config.event_duration) {
			
			function _update_minical_select() {
				ev.start_date = scheduler.date.add(inputs[0]._date, selects[0].value, "minute");
				ev.end_date.setTime(ev.start_date.getTime() + (scheduler.config.event_duration * 60 * 1000));
				
				inputs[1].value = scheduler.templates.calendar_time(ev.end_date);
				inputs[1]._date = scheduler.date.date_part(new Date(ev.end_date));	

				selects[1].value=ev.end_date.getHours()*60+ev.end_date.getMinutes();				
			}
			
			for(var i in selects)
				selects[i].onchange = _update_minical_select;
		}
	
		function _attach_action(inp, date, number){
			_init_once(inp,date,number);
			inp.value = scheduler.templates.calendar_time(date);
			inp._date = scheduler.date.date_part(new Date(date));
		};

		_attach_action(inputs[0],ev.start_date, 0);
		_attach_action(inputs[1],ev.end_date, 1);
		_init_once = function(){};
			
		selects[0].value=ev.start_date.getHours()*60+ev.start_date.getMinutes();
		selects[1].value=ev.end_date.getHours()*60+ev.end_date.getMinutes();
		
	},
	get_value:function(node,ev){
		var inputs = node.getElementsByTagName("input");
		var selects = node.getElementsByTagName("select");		
		
		ev.start_date = scheduler.date.add(inputs[0]._date, selects[0].value, "minute");
		ev.end_date = scheduler.date.add(inputs[1]._date, selects[1].value, "minute");
		
		if (ev.end_date<=ev.start_date) 
			ev.end_date=scheduler.date.add(ev.start_date,scheduler.config.time_step,"minute");
	},
	focus:function(node){
	}
};
scheduler.linkCalendar=function(calendar, datediff){
	var action = function(){
		var date = scheduler._date;
		var mode = scheduler._mode;
		
		var dateNew = new Date(date.valueOf());
		if (datediff) dateNew = datediff(dateNew);
		dateNew.setDate(1);
		scheduler.updateCalendar(calendar, dateNew);
		
		if (!datediff){
			if (mode == 'day') {
				scheduler.markCalendar(calendar,date, "dhx_calendar_click");
			} else if (mode == 'week') {
				dateNew = scheduler.date.week_start(new Date(date.valueOf()));
				for (i = 0; i < 7; i++) {
					var diff = dateNew.getMonth() + dateNew.getYear()*12 - date.getMonth() - date.getYear()*12;
					if (diff && diff>0)
						continue;
					scheduler.markCalendar(calendar, dateNew, "dhx_calendar_click");
					dateNew = scheduler.date.add(dateNew,1,"day");					
				}
			}
		}
		return true;
	};
	
	scheduler.attachEvent("onViewChange", action);
	scheduler.attachEvent("onXLE", action);
	scheduler.attachEvent("onEventAdded", action);
	scheduler.attachEvent("onEventChanged", action);
	scheduler.attachEvent("onAfterEventDelete", action);
	action();
};