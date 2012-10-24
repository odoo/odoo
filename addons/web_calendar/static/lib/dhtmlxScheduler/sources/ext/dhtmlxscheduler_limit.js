/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.config.limit_start = null;
scheduler.config.limit_end   = null;
scheduler.config.limit_view  = false;
scheduler.config.check_limits = true;
scheduler.config.mark_now = true;
scheduler.config.display_marked_timespans = true;

(function(){
	var before = null;
	var dhx_time_block = "dhx_time_block";

	var fix_options = function(options, days, zones) {
		if (days instanceof Date && zones instanceof Date) {
			options.start_date = days;
			options.end_date = zones
		} else {
			options.days = days;
			options.zones = zones;
		}	
		return options;
	};
	var get_resulting_options = function(days, zones, sections) {
		var options = (typeof days == "object") ? days : { days: days };
		options.type = dhx_time_block;
		options.css = "";
		if (zones) {
			if (sections)
				options.sections = sections;
			options = fix_options(options, days, zones);
		}
		return options;
	};
	scheduler.blockTime = function(days, zones, sections){
		var options = get_resulting_options(days, zones, sections);
		return scheduler.addMarkedTimespan(options);
	};
	scheduler.unblockTime = function(days, zones, sections) {
		zones = zones || "fullday";
		var options = get_resulting_options(days, zones, sections);
		return scheduler.deleteMarkedTimespan(options);
	};
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
	var get_relevant_blocked_zones = function(day_index, day_value, zones) {
		var relevant_zones = (zones[day_value] && zones[day_value][dhx_time_block]) ? zones[day_value][dhx_time_block] :
				(zones[day_index] && zones[day_index][dhx_time_block]) ? zones[day_index][dhx_time_block] : [];
		return relevant_zones;
	};
	var blocker = function(event){
		if(!event)
			return true;
		if (!scheduler.config.check_limits)
			return true;
		var s = scheduler;
		var mode = s._mode;
		var timespans = scheduler._marked_timespans;
		var c = s.config;
		var evs = [];
		if (event.rec_type) {
			evs = scheduler.getRecDates(event);
		} else {
			evs = [event];
		}

		var res = true;
		for (var p=0; p<evs.length; p++) {
			var ev = evs[p];

			res = (c.limit_start && c.limit_end) ? (ev.start_date.valueOf() >= c.limit_start.valueOf() && ev.end_date.valueOf() <= c.limit_end.valueOf()) : true;
			if (res){
				var temp_start_date = new Date(ev.start_date.valueOf());
				var temp_end_date = scheduler.date.add(temp_start_date, 1, "day");

				for (; temp_start_date < ev.end_date; temp_start_date = scheduler.date.date_part(temp_end_date), temp_end_date = s.date.add(temp_start_date, 1, "day") ) {
					var day_value = +scheduler.date.date_part( new Date(temp_start_date) ); // the first part of event not necessarily contains only date part
					var day_index = temp_start_date.getDay();

					var zones = [];
					if(s._props && s._props[mode]){
						var view = s._props[mode];
						var block_units = timespans[mode];
						if(block_units && block_units[ev[view.map_to]]) {
							var unit_zones = block_units[ev[view.map_to]];
							var blocked_unit_zones = get_relevant_blocked_zones(day_index, day_value, unit_zones);
							for (var i=0; i<blocked_unit_zones.length; i++) {
								zones = scheduler._add_timespan_zones(zones, blocked_unit_zones[i].zones);
							}
						}
					}
					if (s.matrix && s.matrix[mode]) {
						var timeline_options = s.matrix[mode];
						var timeline_units = timespans[mode];
						if (timeline_units && timeline_units[ev[timeline_options.y_property]]) {
							var timeline_zones = timeline_units[ev[timeline_options.y_property]];
							var blocked_timeline_zones = get_relevant_blocked_zones(day_index, day_value, timeline_zones);
							for (var i=0; i<blocked_timeline_zones.length; i++) {
								zones = scheduler._add_timespan_zones(zones, blocked_timeline_zones[i].zones);
							}
						}
					}
					// now need to add day blocks
					var block_days = timespans.global;
					var blocked_day_zones = get_relevant_blocked_zones(day_index, day_value, block_days)
					for (var i=0; i<blocked_day_zones.length; i++) {
						zones = scheduler._add_timespan_zones(zones, blocked_day_zones[i].zones);
					}

					var sm = scheduler._get_zone_minutes(temp_start_date);
					var em = ( ev.end_date>temp_end_date || ev.end_date.getDate() != temp_start_date.getDate() ) ? 1440 : scheduler._get_zone_minutes(ev.end_date);

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
									if(ev._timed && s._drag_id && s._drag_mode == "new-size"){
										ev.start_date.setHours(0);
										ev.start_date.setMinutes(ez);
									}
									else {
										res = false;
										break;
									}
								}
								if ((em>=sz && em<ez) || (sm < sz && em > ez)){
									if(ev._timed && s._drag_id && s._drag_mode == "new-size"){
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
			}
			if (!res) {
				s._drag_id = null;
				s._drag_mode = null;
				res = (s.checkEvent("onLimitViolation")) ? s.callEvent("onLimitViolation",[ev.id, ev]) : res;
			}
		}
		return res;
	};
	scheduler.attachEvent("onMouseDown", function(classname) {
		return !(classname = dhx_time_block);
	});
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
	scheduler.attachEvent("onEventSave", function(id, data, is_new_event) {
		if(data.rec_type){
			var data_copy = scheduler._lame_clone(data);
			scheduler._roll_back_dates(data_copy);
			return blocker(data);
		}
		return blocker(data);
	});
	scheduler.attachEvent("onEventAdded",function(id){
		if (!id) return true;
		var ev = scheduler.getEvent(id);
		if (!blocker(ev) && scheduler.config.limit_start && scheduler.config.limit_end) {
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
		}
		return true;
	});
	scheduler.attachEvent("onBeforeEventChanged",function(ev, native_object, is_new){
		return blocker(ev);
	});
	scheduler.attachEvent("onBeforeEventCreated", function(ev) { // native event
		var start_date = scheduler.getActionData(ev).date;
		var event = {
			_timed: true,
			start_date: start_date,
			end_date: scheduler.date.add(start_date, scheduler.config.time_step, "minute")
		};
		return blocker(event);
	});

	scheduler.attachEvent("onViewChange", function(){
		scheduler.markNow();
	});
	scheduler.attachEvent("onSchedulerResize", function(){
		window.setTimeout(function(){ scheduler.markNow(); }, 1);
		return true;
	});
	scheduler.attachEvent("onTemplatesReady", function() {
		scheduler._mark_now_timer = window.setInterval(function() {
			scheduler.markNow();
		}, 60000);
	});
	scheduler.markNow = function(hide) {
		// day, week, units views
		var dhx_now_time = 'dhx_now_time';
		if (!this._els[dhx_now_time]) {
			this._els[dhx_now_time] = [];
		}
		var now = scheduler.config.now_date || new Date();
		var cfg = this.config;
		scheduler._remove_mark_now(); // delete previous marks if they exist
		if (!hide && cfg.mark_now && now < this._max_date && now > this._min_date && now.getHours() >= cfg.first_hour && now.getHours()<cfg.last_hour) {
			var day_index = this.locate_holder_day(now);
			this._els[dhx_now_time] = scheduler._append_mark_now(day_index, now);
		}
	};
	scheduler._append_mark_now = function(day_index, now) {
		var dhx_now_time = 'dhx_now_time';
		var zone_start= scheduler._get_zone_minutes(now);
		var options = {
			zones: [zone_start, zone_start+1],
			css: dhx_now_time,
			type: dhx_now_time
		};
		if (!this._table_view) {
			if (this._props && this._props[this._mode]) { // units view
				var day_divs = this._els["dhx_cal_data"][0].childNodes;
				var r_divs = [];

				for (var i=0; i<day_divs.length-1; i++) {
					var t_day = day_index+i; // as each unit is actually considered +1 day
					options.days = t_day;
					var t_div = scheduler._render_marked_timespan(options, null, t_day)[0];
					r_divs.push(t_div)
				}
				return r_divs;
			} else {  // day/week views
				options.days = day_index;
				return scheduler._render_marked_timespan(options, null, day_index);
			}
		} else {
			if (this._mode == "month") {
				options.days = +scheduler.date.date_part(now);
				return scheduler._render_marked_timespan(options, null, null);
			}
		}
	};
	scheduler._remove_mark_now = function() {
		var dhx_now_time = 'dhx_now_time';
		var els = this._els[dhx_now_time];
		for (var i=0; i<els.length; i++) {
			var div = els[i];
			var parent = div.parentNode;
			if (parent) {
				parent.removeChild(div);
			}
		}
		this._els[dhx_now_time] = [];
	};

	/*
	scheduler._marked_timespans = {
		"global": {
			"0": {
				"default": [
					{  // sunday
						zones: [0, 100, 500, 600],
						css: "yellow_box",
						type: "default",
						view: "global",
						day: 0
					}
				]
			}
			"112121312": {
				"my_special_type": [
					{
						zones: [600, 900],
						type: "block",
						css: "some_class",
						view: "global",
						day: 112121312
					},
					{}
				]
			}
		},
		"units": {
			"5_id": {
				"3": {
					"special_type": [ {}, {}, {} ],
					"another_type": [ {} ]
				}
			},
			"6_id": {
				"11212127": {
					...
				}
			}
		}
	}
	*/
	scheduler._marked_timespans = { global: {} };

	scheduler._get_zone_minutes = function(date) {
		return date.getHours()*60 + date.getMinutes();
	};
	scheduler._prepare_timespan_options = function(config) { // receives 1 option, returns array of options
		var r_configs = []; // resulting configs
		var temp_configs = [];

		if (config.days == "fullweek")
			config.days = [0,1,2,3,4,5,6];

		if (config.days instanceof Array) {
			var t_days = config.days.slice();
			for (var i=0; i<t_days.length; i++) {
				var cloned_config = scheduler._lame_clone(config);
				cloned_config.days = t_days[i];
				r_configs.push.apply(r_configs, scheduler._prepare_timespan_options(cloned_config));
			}
			return r_configs;
		}

		if ( !config || !((config.start_date && config.end_date && config.end_date > config.start_date) || (config.days !== undefined && config.zones)) )
			return r_configs;  // incorrect config was provided

		var min = 0;
		var max = 24*60;
		if (config.zones == "fullday")
			config.zones = [min, max];
		if (config.zones && config.invert_zones) {
			config.zones = scheduler.invertZones(config.zones);
		}

		config.id = scheduler.uid();
		config.css = config.css||"";
		config.type = config.type||"default";

		var sections = config.sections;
		if (sections) {
			for (var view_key in sections) {
				if (sections.hasOwnProperty(view_key)) {
					var ids = sections[view_key];
					if (!(ids instanceof Array))
						ids = [ids];
					for (var i=0; i<ids.length; i++) {
						var t_config = scheduler._lame_copy({}, config);
						t_config.sections = {};
						t_config.sections[view_key] = ids[i];
						temp_configs.push(t_config);
					}
				}
			}	
		} else {
			temp_configs.push(config);
		}

		for (var k=0; k<temp_configs.length; k++) {
			var c_config = temp_configs[k]; // config to be checked

			var start_date = c_config.start_date;
			var end_date = c_config.end_date;

			if (start_date && end_date) {
				var t_sd = scheduler.date.date_part(new Date(start_date)); // e.g. 05 october
				var t_ed= scheduler.date.add(t_sd, 1, "day");  // 06 october, will both be incremented in the loop

				while (t_sd < end_date) {
					var t_config = scheduler._lame_copy({}, c_config);
					delete t_config.start_date;
					delete t_config.end_date;
					t_config.days = t_sd.valueOf();
					var zone_start = (start_date > t_sd) ? scheduler._get_zone_minutes(start_date) : min; 
					var zone_end = ( end_date>t_ed || end_date.getDate() != t_sd.getDate() ) ? max : scheduler._get_zone_minutes(end_date);
					t_config.zones = [zone_start, zone_end];
					r_configs.push(t_config);

					t_sd = t_ed;
					t_ed = scheduler.date.add(t_ed, 1, "day");
				}
			} else {
				if (c_config.days instanceof Date)
					c_config.days = (scheduler.date.date_part(c_config.days)).valueOf();
				c_config.zones = config.zones.slice();
				r_configs.push(c_config);
			}
		}
		return r_configs;
	};
	scheduler._get_dates_by_index = function(index, start, end) {
		var dates = [];
		start = start||scheduler._min_date;
		end = end||scheduler._max_date;
		var start_day = start.getDay();
		var delta = (index-start_day >= 0) ? (index-start_day) : (7-start.getDay()+index);
		var t_date = scheduler.date.add(start, delta, "day");
		for (; t_date < end; t_date = scheduler.date.add(t_date, 1, "week")) {
			dates.push(t_date);
		}
		return dates;
	};
	scheduler._get_css_classes_by_config = function(config) {
		var css_classes = [];
		if (config.type == dhx_time_block) {
			css_classes.push(dhx_time_block);
			if (config.css)
				css_classes.push(dhx_time_block+"_reset");
		}
		css_classes.push("dhx_marked_timespan", config.css);
		return css_classes.join(" ");
	};
	scheduler._get_block_by_config = function(config) {
		var block  = document.createElement("DIV");
		if (config.html) {
			if (typeof config.html == "string")
				block.innerHTML = config.html;
			else
				block.appendChild(config.html);
		}
		return block;
	};
	scheduler._render_marked_timespan = function(options, area, day) {
		var blocks = []; // resulting block which will be rendered and returned
		var c = scheduler.config;
		var min_date = this._min_date;
		var max_date = this._max_date;
		var day_value = false; // if timespan for specific date should be displayed

		if (!c.display_marked_timespans)
			return blocks;

		if (!day && day !== 0) { // in case of markTimespan
			if (options.days < 7)
				day = options.days;
			else {
				var date_to_display = new Date(options.days);
				day_value = +date_to_display;

				// in case of markTimespan date could be not in the viewing range, need to return
				if ( !(+max_date >= +date_to_display && +min_date <= +date_to_display) )
					return blocks;

				var day_index = date_to_display.getDay();
				if (scheduler.config.start_on_monday) {
					day = (day_index == 0) ? 6 : day_index-1;
				} else
					day = day_index;
			}
		}
		var zones = options.zones;
		var css_classes = scheduler._get_css_classes_by_config(options);

		if (scheduler._table_view && scheduler._mode == "month") {
			var areas = [];
			var days = [];


			if (!area) {
				days = (day_value) ? [day_value] : scheduler._get_dates_by_index(day);
				for (var i=0; i < days.length; i++) {
					areas.push( this._scales[days[i]] );
				}
			} else {
				areas.push(area);
				days.push(day);
			}

			for (var i=0; i < areas.length; i++) {
				area = areas[i];
				day = days[i];

				for (var k=0; k < zones.length; k+=2) {
					var start = zones[i];
					var end = zones[i+1];
					if (end <= start)
						return [];

					var block = scheduler._get_block_by_config(options);
					block.className = css_classes;

					var height = area.offsetHeight - 1; // 1 for bottom border
					var width = area.offsetWidth - 1; // 1 for left border

					var sweek = Math.floor((this._correct_shift(day,1)-min_date.valueOf())/(60*60*1000*24*this._cols.length));
					var sday = this.locate_holder_day(day, false) % this._cols.length;

					var left = this._colsS[sday];
					var top = this._colsS.heights[sweek]+(this._colsS.height?(this.xy.month_scale_height+2):2)-1;

					block.style.top = top + "px";
					block.style.lineHeight = block.style.height = height + "px";

					block.style.left = (left + Math.round( (start)/(24*60) * width)) + "px";
					block.style.width = Math.round( (end-start)/(24*60) * width) + "px";

					area.appendChild(block);
					blocks.push(block);
				}
			}
		} else {
			area = area ? area : scheduler.locate_holder(day);

			for (var i = 0; i < zones.length; i+=2){
				var start = Math.max(zones[i], c.first_hour*60);
				var end = Math.min(zones[i+1], c.last_hour*60);
				if (end <= start)
					return [];

				var block = scheduler._get_block_by_config(options);
				block.className = css_classes;

				block.style.top = (Math.round((start*60*1000-this.config.first_hour*60*60*1000)*this.config.hour_size_px/(60*60*1000)))%(this.config.hour_size_px*24)+"px";
				block.style.lineHeight = block.style.height = Math.max((Math.round(((end-start-1)*60*1000)*this.config.hour_size_px/(60*60*1000)))%(this.config.hour_size_px*24), 1)+"px";

				area.appendChild(block);
				blocks.push(block);
			}
		}

		return blocks;
	};
	// just marks timespan, will be cleaned after refresh
	scheduler.markTimespan = function(configuration) {
		var configs = scheduler._prepare_timespan_options(configuration);
		if (!configs.length)
			return;
		var divs = [];
		for (var i=0; i<configs.length; i++) {
			var config = configs[i];
			var blocks = scheduler._render_marked_timespan(config, null, null);
			if(blocks.length)
				divs.push.apply(divs, blocks);
		}
		return divs;
	};
	scheduler.unmarkTimespan = function(divs) {
		if (!divs)
			return;
		for (var i=0; i<divs.length; i++) {
			var div = divs[i];
			div.parentNode.removeChild(div);
		}
	};

	scheduler._marked_timespans_ids = {};
	// adds marked timespan to collections, persistent
	scheduler.addMarkedTimespan = function(configuration) {
		var configs = scheduler._prepare_timespan_options(configuration);
		var global = "global";

		if (!configs.length)
			return; // options are incorrect, nothing to mark

		var id = configs[0].id;
		var timespans = scheduler._marked_timespans;
		var ids = scheduler._marked_timespans_ids;
		if (!ids[id])
			ids[id] = [];

		for (var i=0; i<configs.length; i++) {
			var config = configs[i];
			var day = config.days;
			var zones = config.zones;
			var css = config.css;
			var sections = config.sections;
			var type = config.type; // default or specified

			if (sections) {
				for (var view_key in sections) {
					if (sections.hasOwnProperty(view_key)) {
						if (!timespans[view_key])
							timespans[view_key] = {};
						var unit_id = sections[view_key];
						var timespans_view = timespans[view_key];
						if (!timespans_view[unit_id])
							timespans_view[unit_id] = {};
						if (!timespans_view[unit_id][day])
							timespans_view[unit_id][day] = {};
						if (!timespans_view[unit_id][day][type])
							timespans_view[unit_id][day][type] = [];
						var day_configs = timespans_view[unit_id][day][type];
						config._array = day_configs;
						day_configs.push(config);
						ids[id].push(config);
					}
				}
			} else {
				if (!timespans[global][day])
					timespans[global][day] = {};
				if (!timespans[global][day][type])
					timespans[global][day][type] = [];
				var day_configs = timespans[global][day][type];
				config._array = day_configs;
				day_configs.push(config);
				ids[id].push(config);
			}
		}
		return id;
	};
	// not used for now
	scheduler._add_timespan_zones = function(current_zones, zones) {
		var resulting_zones = current_zones.slice();
		zones = zones.slice();

		if (!resulting_zones.length)
			return zones;

		for (var i=0; i<resulting_zones.length; i+=2) {
			var c_zone_start = resulting_zones[i];
			var c_zone_end = resulting_zones[i+1];
			var isLast = (i+2 == resulting_zones.length);

			for (var k=0; k<zones.length; k+=2) {
				var zone_start = zones[k];
				var zone_end = zones[k+1];
				if ((zone_end > c_zone_end && zone_start <= c_zone_end) || (zone_start < c_zone_start && zone_end >= c_zone_start)) {
					resulting_zones[i] = Math.min(c_zone_start, zone_start);
					resulting_zones[i+1] = Math.max(c_zone_end, zone_end);
					i -= 2;
				} else {
					if (!isLast) // do nothing, maybe next current zone will match or will be last
						continue;

					var offset = (c_zone_start > zone_start)?0:2;
					resulting_zones.splice(i+offset, 0, zone_start, zone_end); // last current zone, need to add another
				}
				zones.splice(k--,2); // zone was merged or added, need to exclude it
				break;
			}
		}
		return resulting_zones;
	};
	scheduler._subtract_timespan_zones = function(current_zones, zones) {
		var resulting_zones = current_zones.slice();
		for (var i=0; i<resulting_zones.length; i+=2 ) {
			var c_zone_start = resulting_zones[i];// current_zone_start
			var c_zone_end = resulting_zones[i+1];
			for (var k=0; k<zones.length; k+=2) {
				var zone_start = zones[k];
				var zone_end = zones[k+1];
				if (zone_end > c_zone_start && zone_start < c_zone_end) {
					var is_modified = false;
					if (c_zone_start >= zone_start && c_zone_end <= zone_end) {
						resulting_zones.splice(i, 2);
					}				
					if (c_zone_start < zone_start) {
						resulting_zones.splice(i, 2, c_zone_start, zone_start);
						is_modified = true;
					}
					if (c_zone_end > zone_end) {
						resulting_zones.splice( (is_modified)?(i+2):i, (is_modified)?0:2, zone_end, c_zone_end);
					}
					i -= 2;
					break;
				} else {
					continue;
				}
			}
		}
		return resulting_zones;
	};
	scheduler.invertZones = function(zones) {
		return scheduler._subtract_timespan_zones([0, 1440], zones.slice());
	};
	scheduler._delete_marked_timespan_by_id = function(id) {
		var configs = scheduler._marked_timespans_ids[id];
		if (configs) {
			for (var i=0; i<configs.length; i++) {
				var config = configs[i];
				var parent_array = config._array;
				for (var k=0; k<parent_array.length; k++) {
					if (parent_array[k] == config) {
						parent_array.splice(k, 1);
						break;
					}
				}
			}
		}
	};
	scheduler._delete_marked_timespan_by_config = function(config) {
		var timespans = scheduler._marked_timespans;
		var sections = config.sections;
		var day = config.days;
		var type = config.type||"default";
		var day_timespans = []; // array of timespans to subtract our config
		if (sections) {
			for (var view_key in sections) {
				if (sections.hasOwnProperty(view_key) && timespans[view_key]) {
					var unit_id = sections[view_key];
					if (timespans[view_key][unit_id] && timespans[view_key][unit_id][day] && timespans[view_key][unit_id][day][type])
						day_timespans = timespans[view_key][unit_id][day][type];
				}
			}
		} else {
			if (timespans.global[day] && timespans.global[day][type])
				day_timespans = timespans.global[day][type];
		}
		for (var i=0; i<day_timespans.length; i++) {
			var d_t = day_timespans[i];
			var zones = scheduler._subtract_timespan_zones(d_t.zones, config.zones);
			if (zones.length)
				d_t.zones = zones;
			else {
				day_timespans.splice(i,1);
				i--;
				// need to update ids collection
				var related_zones = scheduler._marked_timespans_ids[d_t.id];
				for (var k=0; k<related_zones.length; k++) {
					if (related_zones[k] == d_t) {
						related_zones.splice(k, 1);
						break;
					}
				}
			}
		}
	};
	scheduler.deleteMarkedTimespan = function(configuration) {
		if (!arguments.length) // delete everything
			scheduler._marked_timespans = { global: {} }; 
		if (typeof configuration != "object") { // id was passed
			scheduler._delete_marked_timespan_by_id(configuration);
		} else { // normal configuration was passed
			var configs = scheduler._prepare_timespan_options(configuration);
			for (var i=0; i<configs.length; i++) {
				var config = configs[i];
				scheduler._delete_marked_timespan_by_config(configs[i]);
			}
		}
	};
	scheduler._get_types_to_render = function(common, specific) {
		var types_to_render = (common) ? common : {};
		for (var type in specific||{} ) {
			if (specific.hasOwnProperty(type)) {
				types_to_render[type] = specific[type];
			}
		}
		return types_to_render;
	};
	scheduler._get_configs_to_render = function(types) {
		var configs = [];
		for (var type in types) {
			if (types.hasOwnProperty(type)) {
				configs.push.apply(configs, types[type]);
			}
		}
		return configs;
	};
	scheduler.attachEvent("onScaleAdd", function(area, day) {
		if (scheduler._table_view && scheduler._mode != "month")
			return;

		var day_index = day.getDay();
		var day_value = day.valueOf();
		var mode = this._mode;
		var timespans = scheduler._marked_timespans;
		var r_configs = [];

		if (this._props && this._props[mode]) { // we are in the units view and need to draw it's sections as well
			var view = this._props[mode]; // units view object
			var units = view.options;
			var index = (view.position||0)+Math.floor((this._correct_shift(day.valueOf(),1)-this._min_date.valueOf())/(60*60*24*1000)); // user index
			var unit = units[index]; // key, label
			day = scheduler.date.date_part(new Date(this._date)); // for units view actually only 1 day is displayed yet the day variable will change, need to use this._date for all calls
			day_index = day.getDay();
			day_value = day.valueOf();

			if (timespans[mode] && timespans[mode][unit.key]) {
				var unit_zones = timespans[mode][unit.key];
				var unit_types = scheduler._get_types_to_render(unit_zones[day_index], unit_zones[day_value]);
				r_configs.push.apply(r_configs, scheduler._get_configs_to_render(unit_types));
			}
		}

		var global_data = timespans["global"];
		var day_types = global_data[day_value]||global_data[day_index];
		r_configs.push.apply(r_configs, scheduler._get_configs_to_render(day_types));

		for (var i=0; i<r_configs.length; i++) {
			scheduler._render_marked_timespan(r_configs[i], area, day);
		}
	});	

})();
