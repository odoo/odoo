/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){

var temp_section;
var before;

scheduler.config.collision_limit = 1;	

function _setTempSection(event_id) { // for custom views (matrix, timeline, units)
	var pr = scheduler._props?scheduler._props[scheduler._mode]:null;
	var matrix = scheduler.matrix?scheduler.matrix[scheduler._mode]:null;
	var checked_mode = pr||matrix; // units or matrix mode
	if(pr)
		var map_to = checked_mode.map_to;
	if(matrix)
		var map_to = checked_mode.y_property;
	if ((checked_mode) && event_id){
		temp_section = scheduler.getEvent(event_id)[map_to];
	}	
}

scheduler.attachEvent("onBeforeDrag",function(id){
	_setTempSection(id); 
	return true;
});
scheduler.attachEvent("onBeforeLightbox",function(id){
	var ev = scheduler.getEvent(id);
	before = [ev.start_date, ev.end_date];
	_setTempSection(id);
	return true;
});
scheduler.attachEvent("onEventChanged",function(id){
	if (!id) return true;
	var ev = scheduler.getEvent(id);
	if (!collision_check(ev)){
		if (!before) return false;
		ev.start_date = before[0];
		ev.end_date = before[1];
		ev._timed=this.is_one_day_event(ev);
	}
	return true;
});
scheduler.attachEvent("onBeforeEventChanged",function(ev,e,is_new){
	return collision_check(ev);
});
scheduler.attachEvent("onEventSave",function(id, edited_ev, is_new){
	edited_ev = scheduler._lame_clone(edited_ev);
	edited_ev.id = id;

	if(edited_ev.rec_type){
		scheduler._roll_back_dates(data_copy);
	}
	return collision_check(edited_ev); // in case user creates event on one date but then edited it another
});

function collision_check(ev){
	var evs = [];
	var collision_limit = scheduler.config.collision_limit;
	if (ev.rec_type) {
		var evs_dates = scheduler.getRecDates(ev);
		for(var k=0; k<evs_dates.length; k++) {
			var tevs = scheduler.getEvents(evs_dates[k].start_date, evs_dates[k].end_date);
			for(var j=0; j<tevs.length; j++) { 
				if ((tevs[j].event_pid || tevs[j].id) != ev.id )
					evs.push(tevs[j]);
			}
		}
	} else {
		evs = scheduler.getEvents(ev.start_date, ev.end_date);
		for (var i=0; i<evs.length; i++) {
			if (evs[i].id == ev.id) {
				evs.splice(i,1);
				break;
			}
		}
	}
	
	var pr = scheduler._props?scheduler._props[scheduler._mode]:null;
	var matrix = scheduler.matrix?scheduler.matrix[scheduler._mode]:null;
	
	var checked_mode = pr||matrix;
	if(pr)
		var map_to = checked_mode.map_to;
	if(matrix)
		var map_to = checked_mode.y_property;
	
	var single = true;
	if (checked_mode) { // custom view
		var count = 0;

		for (var i = 0; i < evs.length; i++)

			if (evs[i][map_to] == ev[map_to] && evs[i].id != ev.id)
				count++;
				
		if (count >= collision_limit) {

			single = false;
		}
	}
	else {
		if ( evs.length >= collision_limit )
			single = false;
	}
	if (!single) {
		var res = !scheduler.callEvent("onEventCollision",[ev,evs]);
		if (!res) {
			ev[map_to] = temp_section||ev[map_to]; // from _setTempSection for custom views
		}
		return res;
	}
	return single;
	
}

})();
