/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.date.add_agenda = function(date){
	return (new Date(date.valueOf()));
};

scheduler.dblclick_dhx_agenda_area=function(){
	if (!this.config.readonly && this.config.dblclick_create)
		this.addEventNow();
};
scheduler.templates.agenda_time = function(start,end,ev){
	if (ev._timed) 
		return this.day_date(ev.start_date, ev.end_date, ev)+" "+this.event_date(start);
	else
		return scheduler.templates.day_date(start)+" &ndash; "+scheduler.templates.day_date(end);
};
scheduler.templates.agenda_text = function(start,end,event){
	return event.text;
};
scheduler.date.agenda_start=function(d){ return d; };
	
scheduler.attachEvent("onTemplatesReady",function(){



	scheduler.attachEvent("onSchedulerResize",function(){
	   if (this._mode == "agenda"){
	      this.agenda_view(true);
	      return false;
	   }
	   return true;
	});
	
	
	var old = scheduler.render_data;
	scheduler.render_data=function(evs){
		if (this._mode == "agenda")
   			fill_agenda_tab();
   		else
   			return old.apply(this,arguments);
	}
	
	var old_render_view_data = scheduler.render_view_data;
	scheduler.render_view_data=function(){
		if(this._mode == "agenda") {
			scheduler._agendaScrollTop = scheduler._els["dhx_cal_data"][0].childNodes[0].scrollTop;
			scheduler._els["dhx_cal_data"][0].childNodes[0].scrollTop = 0;
			scheduler._els["dhx_cal_data"][0].style.overflowY = 'hidden';
		}
		else {
			scheduler._els["dhx_cal_data"][0].style.overflowY = 'auto';
		}
		return old_render_view_data.apply(this,arguments);
	}


	function set_full_view(mode){
		if (mode){
			var l = scheduler.locale.labels;
			scheduler._els["dhx_cal_header"][0].innerHTML="<div class='dhx_agenda_line'><div>"+l.date+"</div><span style='padding-left:25px'>"+l.description+"</span></div>";
			scheduler._table_view=true;
			scheduler.set_sizes();
		}
	}

	function fill_agenda_tab(){
		//get current date
		var date = scheduler._date;
		//select events for which data need to be printed
		
		var events = scheduler.get_visible_events();
		events.sort(function(a,b){ return a.start_date>b.start_date?1:-1});
		
		//generate html for the view
		var html="<div class='dhx_agenda_area'>";
		for (var i=0; i<events.length; i++){
			var ev = events[i];
            var bg_color = (ev.color?("background-color:"+ev.color+";"):"");
            var color = (ev.textColor?("color:"+ev.textColor+";"):"");
			html+="<div class='dhx_agenda_line' event_id='"+ev.id+"' style='"+color+""+bg_color+""+(ev._text_style||"")+"'><div>"+scheduler.templates.agenda_time(ev.start_date, ev.end_date,ev)+"</div>";
			html+="<div class='dhx_event_icon icon_details'>&nbsp</div>";
			html+="<span>"+scheduler.templates.agenda_text(ev.start_date, ev.end_date, ev)+"</span></div>";
		}
		html+="<div class='dhx_v_border'></div></div>";
			
		//render html
		scheduler._els["dhx_cal_data"][0].innerHTML = html;
		scheduler._els["dhx_cal_data"][0].childNodes[0].scrollTop = scheduler._agendaScrollTop||0;
		
		var t=scheduler._els["dhx_cal_data"][0].firstChild.childNodes;
		scheduler._els["dhx_cal_date"][0].innerHTML="";
		
		scheduler._rendered=[];
		for (var i=0; i < t.length-1; i++)
			scheduler._rendered[i]=t[i]
		
	}

	scheduler.agenda_view=function(mode){
		scheduler._min_date = scheduler.config.agenda_start||(new Date());
		scheduler._max_date = scheduler.config.agenda_end||(new Date(9999,1,1));
		scheduler._table_view = true;
		set_full_view(mode);
		if (mode){
			//agenda tab activated
			fill_agenda_tab();
		} else {
			//agenda tab de-activated
		}
	}
})
