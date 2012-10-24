/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){

	scheduler.config.all_timed = "short";
	scheduler.config.update_render = true;

	var is_event_short = function (ev) {
		return 	!((ev.end_date - ev.start_date)/(1000*60*60) >= 24);
	};

	var old_prerender_events_line = scheduler._pre_render_events_line;
	scheduler._pre_render_events_line = function(evs, hold){
		if (!this.config.all_timed)
			return old_prerender_events_line.call(this, evs, hold);

		for (var i=0; i < evs.length; i++) {
			var ev=evs[i];

			if (!ev._timed) {

				if (this.config.all_timed == "short") {
					if (!is_event_short(ev)) {
						evs.splice(i--,1);
						continue;
					}
				}

				var ce = this._lame_copy({}, ev); // current event (event for one specific day) is copy of original with modified dates
				
				ce.start_date = new Date(ce.start_date); // as lame copy doesn't copy date objects

				var next_day = scheduler.date.add(ev.start_date, 1, "day");
				next_day = scheduler.date.date_part(next_day);

				if (ev.end_date < next_day) {
					ce.end_date = new Date(ev.end_date);
				}
				else {
					ce.end_date = next_day;
					if (this.config.last_hour != 24) { // if specific last_hour was set (e.g. 20)
						ce.end_date = scheduler.date.date_part(new Date(ce.start_date));
						ce.end_date.setHours(this.config.last_hour);
					}
				}

				var event_changed = false;
				if (ce.start_date < this._max_date && ce.end_date > this._min_date && ce.start_date < ce.end_date) {
					evs[i] = ce; // adding another event in collection
					event_changed = true;
				}
				if (ce.start_date > ce.end_date) {
					evs.splice(i--,1);
				}

				var re = this._lame_copy({}, ev); // remaining event, copy of original with modified start_date (making range more narrow)
				re.end_date = new Date(re.end_date);
				if (re.start_date < this._min_date)
					re.start_date = new Date(this._min_date);
				else
					re.start_date = this.date.add(ev.start_date, 1, "day");

				re.start_date.setHours(this.config.first_hour);
				re.start_date.setMinutes(0); // as we are starting only with whole hours
				if (re.start_date < this._max_date && re.start_date < re.end_date) {
					if (event_changed)
						evs.splice(i+1,0,re);
					else {
						evs[i--] = re;
						continue;
					}
				}
			}
		}
		// in case of all_timed pre_render is not applied to the original event
		// so we need to force redraw in case of dnd
		var redraw = (this._drag_mode == 'move')?false:hold;
		return old_prerender_events_line.call(this, evs, redraw);
	};
	var old_get_visible_events = scheduler.get_visible_events;
	scheduler.get_visible_events = function(only_timed){
		if (!this.config.all_timed)
			return old_get_visible_events.call(this, only_timed);	
		return old_get_visible_events.call(this, false); // only timed = false
	};
	scheduler.attachEvent("onBeforeViewChange", function (old_mode, old_date, mode, date) {
		scheduler._allow_dnd = (mode == "day" || mode == "week");
		return true;
	});

	scheduler.render_view_data=function(evs, hold){
		if(!evs){
			if (this._not_render) {
				this._render_wait=true;
				return;
			}
			this._render_wait=false;

			this.clear_view();
			evs=this.get_visible_events( !(this._table_view || this.config.multi_day) );
		}

		if (this.config.multi_day && !this._table_view){

			var tvs = [];
			var tvd = [];
			for (var i=0; i < evs.length; i++){
				if (evs[i]._timed || this.config.all_timed === true || (this.config.all_timed == "short" && is_event_short(evs[i])) )
					tvs.push(evs[i]);
				else
					tvd.push(evs[i]);
			}

			// normal events
			this._rendered_location = this._els['dhx_cal_data'][0];
			this._table_view=false;
			this.render_data(tvs, hold);

			// multiday events
			this._rendered_location = this._els['dhx_multi_day'][0];
			this._table_view = true;
			this.render_data(tvd, hold);
			this._table_view=false;

		} else {
			this._rendered_location = this._els['dhx_cal_data'][0];
			this.render_data(evs, hold);
		}
	};

})();