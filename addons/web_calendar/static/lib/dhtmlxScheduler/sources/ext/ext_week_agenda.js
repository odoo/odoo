/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler._wa = {};
scheduler.xy.week_agenda_scale_height = 20;
scheduler.templates.week_agenda_event_text = function(start_date, end_date, event, date) {
	return scheduler.templates.event_date(start_date) + " " + event.text;
};
scheduler.date.week_agenda_start = scheduler.date.week_start;
scheduler.date.week_agenda_end = function(date){
	return scheduler.date.add(date, 7, "day");
};
scheduler.date.add_week_agenda = function(date, inc){
	return scheduler.date.add(date, inc*7, "day");
};

scheduler.attachEvent("onSchedulerReady", function(){
	var t = scheduler.templates;
	if(!t.week_agenda_date)
		t.week_agenda_date = t.week_date;
});

(function(){
	var scale_date_format = scheduler.date.date_to_str("%l, %F %d");
	scheduler.templates.week_agenda_scale_date = function(date) {
		return scale_date_format(date);
	};
})();

scheduler.attachEvent("onTemplatesReady", function() {

	scheduler.attachEvent("onSchedulerResize", function() {
		if (this._mode == "week_agenda") {
			this.week_agenda_view(true);
			return false;
		}
		return true;
	});

	var old = scheduler.render_data;
	scheduler.render_data = function(evs) {
		if (this._mode == "week_agenda") {
			fillWeekAgendaTab();
		}
		else
			return old.apply(this, arguments);
	};

	var getColumnSizes = function() {
		// widths
		scheduler._cols = [];
		var twidth = parseInt(scheduler._els['dhx_cal_data'][0].style.width);
		scheduler._cols.push(Math.floor(twidth / 2));
		scheduler._cols.push(twidth - scheduler._cols[0] - 1); // To add border between columns

		// heights
		scheduler._colsS = {
			0: [],
			1: []
		};
		var theight = parseInt(scheduler._els['dhx_cal_data'][0].style.height);
		for (var i = 0; i < 3; i++) {
			scheduler._colsS[0].push(Math.floor(theight / (3 - scheduler._colsS[0].length)));
			theight -= scheduler._colsS[0][i];
		}
		scheduler._colsS[1].push(scheduler._colsS[0][0]);
		scheduler._colsS[1].push(scheduler._colsS[0][1]);
		// last two days
		theight = scheduler._colsS[0][scheduler._colsS[0].length - 1];
		scheduler._colsS[1].push(Math.floor(theight / 2));
		scheduler._colsS[1].push(theight - scheduler._colsS[1][scheduler._colsS[1].length - 1]);
	};
	var fillWeekAgendaTab = function() {
		scheduler._els["dhx_cal_data"][0].innerHTML = '';
		var html = '';
		for (var i = 0; i < 2; i++) {
			var width = scheduler._cols[i];
			var column_css = 'dhx_wa_column';
			if (i == 1)
				column_css += ' dhx_wa_column_last';
			html += "<div class='" + column_css + "' style='width: " + width + "px;'>";
			for (var k = 0; k < scheduler._colsS[i].length; k++) {
				var scale_height = scheduler.xy.week_agenda_scale_height - 2;
				var height = scheduler._colsS[i][k] - scale_height - 2;
				html += "<div class='dhx_wa_day_cont'><div style='height:" + scale_height + "px; line-height:" + scale_height + "px;' class='dhx_wa_scale_bar'></div><div style='height:" + height + "px;' class='dhx_wa_day_data'></div></div>";
			}
			html += "</div>";
		}
		scheduler._els["dhx_cal_date"][0].innerHTML = scheduler.templates[scheduler._mode+"_date"](scheduler._min_date, scheduler._max_date, scheduler._mode);
		scheduler._els["dhx_cal_data"][0].innerHTML = html;
		var all_divs = scheduler._els["dhx_cal_data"][0].getElementsByTagName('div');
		var day_divs = [];
		for (var i = 0; i < all_divs.length; i++) {
			if (all_divs[i].className == 'dhx_wa_day_cont')
				day_divs.push(all_divs[i]);
		}
		scheduler._wa._selected_divs = [];
        var events = scheduler.get_visible_events(); // list of events to be displayed in current week
		var tstart = scheduler.date.week_start(scheduler._date);
		var tend = scheduler.date.add(tstart, 1, "day");
		for (var i = 0; i < 7; i++) {
			day_divs[i]._date = tstart;
			var scale_bar = day_divs[i].childNodes[0];
			var events_div = day_divs[i].childNodes[1];
			scale_bar.innerHTML = scheduler.templates.week_agenda_scale_date(tstart);
            var evs = []; // events which will be displayed in the current day
            for (var j = 0; j < events.length; j++) {
                var tev = events[j];
                if(tev.start_date<tend && tev.end_date>tstart)
                    evs.push(tev);
            }
			evs.sort(function(a,b){
				if(a.start_date.valueOf()==b.start_date.valueOf())
					return a.id>b.id?1:-1;
				return a.start_date>b.start_date?1:-1;
			});
			for (var k = 0; k < evs.length; k++) {
				var ev = evs[k];
				var ev_div = document.createElement('div');
				scheduler._rendered.push(ev_div);
				ev_div.className = 'dhx_wa_ev_body';
                if(ev._text_style)
                    ev_div.style.cssText = ev._text_style;
				if(ev.color)
					ev_div.style.backgroundColor = ev.color;
				if(ev.textColor)
					ev_div.style.color = ev.textColor;
				if(scheduler._select_id && ev.id == scheduler._select_id) {
					ev_div.className += " dhx_cal_event_selected";
					scheduler._wa._selected_divs.push(ev_div);
				}
				var position = "";
				if(!ev._timed){
					position = "middle";
					if(ev.start_date.valueOf() >= tstart.valueOf() && ev.start_date.valueOf() <= tend.valueOf())
						position = "start";
					if(ev.end_date.valueOf() >= tstart.valueOf() && ev.end_date.valueOf() <= tend.valueOf())
						position = "end";
				}
				ev_div.innerHTML = scheduler.templates.week_agenda_event_text(ev.start_date, ev.end_date, ev, tstart, position);
				ev_div.setAttribute('event_id', ev.id);
				events_div.appendChild(ev_div);
			}
			tstart = scheduler.date.add(tstart, 1, "day");
			tend = scheduler.date.add(tend, 1, "day");
		}
	};
	scheduler.week_agenda_view = function(mode) {
		scheduler._min_date = scheduler.date.week_start(scheduler._date);
		scheduler._max_date = scheduler.date.add(scheduler._min_date, 1, "week");
		scheduler.set_sizes();
		if (mode) { // mode enabled
			scheduler._table_view=true;

			// hiding default top border from dhx_cal_data
			scheduler._wa._prev_data_border = scheduler._els['dhx_cal_data'][0].style.borderTop;
			scheduler._els['dhx_cal_data'][0].style.borderTop = 0;
			scheduler._els['dhx_cal_data'][0].style.overflowY = 'hidden';

            // cleaning dhx_cal_date from the previous date
            scheduler._els['dhx_cal_date'][0].innerHTML = "";

			// 1 to make navline to be over data
			scheduler._els['dhx_cal_data'][0].style.top = (parseInt(scheduler._els['dhx_cal_data'][0].style.top)-scheduler.xy.bar_height-1) + 'px';
			scheduler._els['dhx_cal_data'][0].style.height = (parseInt(scheduler._els['dhx_cal_data'][0].style.height)+scheduler.xy.bar_height+1) + 'px';
			
			scheduler._els['dhx_cal_header'][0].style.display = 'none';
			getColumnSizes();
			fillWeekAgendaTab();
		}
		else { // leaving week_agenda mode
			scheduler._table_view=false;

			// restoring default top border to dhx_cal_data
			if (scheduler._wa._prev_data_border)
				scheduler._els['dhx_cal_data'][0].style.borderTop = scheduler._wa._prev_data_border;

			scheduler._els['dhx_cal_data'][0].style.overflowY = 'auto';
			scheduler._els['dhx_cal_data'][0].style.top = (parseInt(scheduler._els['dhx_cal_data'][0].style.top)+scheduler.xy.bar_height) + 'px';
			scheduler._els['dhx_cal_data'][0].style.height = (parseInt(scheduler._els['dhx_cal_data'][0].style.height)-scheduler.xy.bar_height) + 'px';
			scheduler._els['dhx_cal_header'][0].style.display = 'block';
		}
	};
	scheduler.mouse_week_agenda = function(pos) {
		var native_event = pos.ev;
		var src = native_event.srcElement || native_event.target;
		while (src.parentNode) {
			if (src._date)
				var date = src._date;
			src = src.parentNode;
		}
		if(!date)
			return pos;
		pos.x = 0;
		var diff = date.valueOf() - scheduler._min_date.valueOf();
		pos.y = Math.ceil(( diff / (1000 * 60) ) / this.config.time_step);
		if (this._drag_mode == 'move') {
			this._drag_event._dhx_changed = true;
			this._select_id = this._drag_id;
			for (var i = 0; i < scheduler._rendered.length; i++) {
				if (scheduler._drag_id == this._rendered[i].getAttribute('event_id'))
					var event_div = this._rendered[i];
			}
			if (!scheduler._wa._dnd) {
				var div = event_div.cloneNode(true);
				this._wa._dnd = div;
				div.className = event_div.className;
				div.id = 'dhx_wa_dnd';
				div.className += ' dhx_wa_dnd';
				document.body.appendChild(div);
			}
			var dnd_div = document.getElementById('dhx_wa_dnd');
			dnd_div.style.top = ((native_event.pageY || native_event.clientY) + 20) + "px";
			dnd_div.style.left = ((native_event.pageX || native_event.clientX) + 20) + "px";
		}
		return pos;
	};
	scheduler.attachEvent('onBeforeEventChanged', function(event_object, native_event, is_new) {
		if (this._mode == 'week_agenda') {
			if (this._drag_mode == 'move') {
				var dnd = document.getElementById('dhx_wa_dnd');
				dnd.parentNode.removeChild(dnd);
				scheduler._wa._dnd = false;
			}
		}
		return true;
	});

	scheduler.attachEvent("onEventSave",function(id,data,is_new_event){
		if(is_new_event)
			this._select_id = id;
		return true;
	});

	scheduler._wa._selected_divs = [];

	scheduler.attachEvent("onClick",function(event_id, native_event_object){
	    if(this._mode == 'week_agenda'){
			if(scheduler._wa._selected_divs) {
				for(var i=0; i<this._wa._selected_divs.length; i++) {
					var div = this._wa._selected_divs[i];
					div.className = div.className.replace(/ dhx_cal_event_selected/,'');
				}
			}
			this.for_rendered(event_id, function(event_div){
				event_div.className += " dhx_cal_event_selected";
				scheduler._wa._selected_divs.push(event_div);
			});
			this._select_id = event_id;
			return false;
	    }
	    return true;
    });
});
