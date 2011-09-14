/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.config.limit_start = new Date(-3999,0,0);
scheduler.config.limit_end   = new Date( 3999,0,0);
scheduler.config.limit_view  = false;

(function(){
	var before = null;
	
	var block_days = {};
	var block_weeks = {};
	var time_block_set = false;
	scheduler.blockTime = function(day, zones){
		var bottom = this.config.first_hour*60
		var top = this.config.last_hour*60
		if (zones == "fullday")
			zones = [bottom,top];

		if (typeof day == "object")
			block_days[this.date.date_part(day).valueOf()] = zones;
		else
			block_weeks[day] = zones;

		for (var i=0; i<zones.length; i+=2){
			if (zones[i]<bottom)
				zones[i] = bottom;
			if (zones[i+1]>top)
				zones[i+1] = top;
		}

		time_block_set = true;
	};

	scheduler.attachEvent("onScaleAdd", function(area, day){
		var zones = block_days[day.valueOf()] || block_weeks[day.getDay()];
		if (zones){
			for (var i = 0; i < zones.length; i+=2){
				var start = zones[i];
				var end = zones[i+1];
				var block  = document.createElement("DIV");
				block.className = "dhx_time_block";

                var h_px // FIXME
				block.style.top = (Math.round((start*60*1000-this.config.first_hour*60*60*1000)*this.config.hour_size_px/(60*60*1000)))%(this.config.hour_size_px*24)+"px"; 
				block.style.height = (Math.round(((end-start-1)*60*1000)*this.config.hour_size_px/(60*60*1000)))%(this.config.hour_size_px*24)+"px"; 

				area.appendChild(block);
			}
		}
	});

	scheduler.attachEvent("onBeforeViewChange",function(om,od,nm,nd){
		nd = nd||od; nm = nm||om;
		if (scheduler.config.limit_view){
			if (nd.valueOf()>scheduler.config.limit_end.valueOf() || this.date.add(nd,1,nm)<=scheduler.config.limit_start.valueOf()){
				setTimeout(function(){
					scheduler.setCurrentView(scheduler._date, nm);
				},1);
				return false;
			}
		}
		return true;
	});
	var blocker = function(ev){
		var c = scheduler.config;
		var res = (ev.start_date.valueOf() >= c.limit_start.valueOf() && ev.end_date.valueOf() <= c.limit_end.valueOf());
		if (res && time_block_set && ev._timed){
			var day = scheduler.date.date_part(new Date(ev.start_date.valueOf()));
			var zones = block_days[day.valueOf()] || block_weeks[day.getDay()];
			var sm = ev.start_date.getHours()*60+ev.start_date.getMinutes();
			var em = ev.end_date.getHours()*60+ev.end_date.getMinutes();
			if (zones){
				for (var i = 0; i < zones.length; i+=2){
					var sz = zones[i];
					var ez = zones[i+1];
					if (sz<em && ez>sm) {
						if (sm<=ez && sm >=sz){
							if (ez == 24*60 || em<ez){
								res = false;
								break;
							}
                            if(scheduler._drag_id && scheduler._drag_mode == "new-size"){
                                ev.start_date.setHours(0);
                                ev.start_date.setMinutes(ez);
                            }
                            else {
                                res = false;
                                break;
                            }
						}
						if (em>=sz && em<ez){
                            if(scheduler._drag_id && scheduler._drag_mode == "new-size"){
                                ev.end_date.setHours(0);
                                ev.end_date.setMinutes(sz);
                            }
                            else {
                                res = false;
                                break;
                            }
						}
					}
				}
			}
		}
		if (!res) {
			scheduler._drag_id = null;
			scheduler._drag_mode = null;
			scheduler.callEvent("onLimitViolation",[ev.id, ev]);
		}
		return res;
	};
	
	scheduler.attachEvent("onBeforeDrag",function(id){
		if (!id) return true;
		return blocker(scheduler.getEvent(id));
	});
	scheduler.attachEvent("onClick", function (event_id, native_event_object){
		return blocker(scheduler.getEvent(event_id));
    });
	scheduler.attachEvent("onBeforeLightbox",function(id){
        
		var ev = scheduler.getEvent(id);
		before = [ev.start_date, ev.end_date];
		return blocker(ev);
	});	
	scheduler.attachEvent("onEventAdded",function(id){
		if (!id) return true;
		var ev = scheduler.getEvent(id);
		if (!blocker(ev)){
			if (ev.start_date < scheduler.config.limit_start) {
				ev.start_date = new Date(scheduler.config.limit_start);
			}
			if (ev.start_date.valueOf() >= scheduler.config.limit_end.valueOf()) {
				ev.start_date = this.date.add(scheduler.config.limit_end, -1, "day");
			}			
			if (ev.end_date < scheduler.config.limit_start) {
				ev.end_date = new Date(scheduler.config.limit_start);
			}			
			if (ev.end_date.valueOf() >= scheduler.config.limit_end.valueOf()) {
				ev.end_date = this.date.add(scheduler.config.limit_end, -1, "day");
			}
			if (ev.start_date.valueOf() >= ev.end_date.valueOf()) { 
				ev.end_date = this.date.add(ev.start_date, (this.config.event_duration||this.config.time_step), "minute");
			}
			ev._timed=this.is_one_day_event(ev);
		}
		return true;
	});
	scheduler.attachEvent("onEventChanged",function(id){
		if (!id) return true;
		var ev = scheduler.getEvent(id);
		if (!blocker(ev)){
			if (!before) return false;
			ev.start_date = before[0];
			ev.end_date = before[1];
			ev._timed=this.is_one_day_event(ev);
		};
		return true;
	});
	scheduler.attachEvent("onBeforeEventChanged",function(ev, native_object, is_new){
		return blocker(ev);
	});

})();