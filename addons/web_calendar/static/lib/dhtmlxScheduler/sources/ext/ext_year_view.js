/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.config.year_x = 4;
scheduler.config.year_y = 3;
scheduler.config.year_mode_name = "year";
scheduler.xy.year_top = 0;

scheduler.templates.year_date = function(date) {
	return scheduler.date.date_to_str(scheduler.locale.labels.year_tab + " %Y")(date);
};
scheduler.templates.year_month = scheduler.date.date_to_str("%F");
scheduler.templates.year_scale_date = scheduler.date.date_to_str("%D");
scheduler.templates.year_tooltip = function(s, e, ev) {
	return ev.text
};

(function() {
	var is_year_mode = function() {
		return scheduler._mode == scheduler.config.year_mode_name;
	};

	scheduler.dblclick_dhx_month_head = function(e) {
		if (is_year_mode()) {
			var t = (e.target || e.srcElement);
			if (t.parentNode.className.indexOf("dhx_before") != -1 || t.parentNode.className.indexOf("dhx_after") != -1) return false;
			var start = this.templates.xml_date(t.parentNode.parentNode.parentNode.parentNode.parentNode.parentNode.getAttribute("date"));
			start.setDate(parseInt(t.innerHTML, 10));
			var end = this.date.add(start, 1, "day")
			if (!this.config.readonly && this.config.dblclick_create)
				this.addEventNow(start.valueOf(), end.valueOf(), e);
		}
	};

	var chid = scheduler.changeEventId;
	scheduler.changeEventId = function() {
		chid.apply(this, arguments);
		if (is_year_mode())
			this.year_view(true);
	};


	var old = scheduler.render_data;
	var to_attr = scheduler.date.date_to_str("%Y/%m/%d");
	var from_attr = scheduler.date.str_to_date("%Y/%m/%d");
	scheduler.render_data = function(evs) {
		if (!is_year_mode()) return old.apply(this, arguments);
		for (var i = 0; i < evs.length; i++)
			this._year_render_event(evs[i]);
	};

	var clear = scheduler.clear_view;
	scheduler.clear_view = function() {
		if (!is_year_mode()) return clear.apply(this, arguments);
		for (var i = 0; i < marked.length; i++) {
			marked[i].className = "dhx_month_head";
			marked[i].setAttribute("date", "")
		}
		marked = [];
	};

	scheduler.hideToolTip = function() {
		if (this._tooltip) {
			this._tooltip.style.display = "none";
			this._tooltip.date = new Date(9999, 1, 1);
		}
	};

	scheduler.showToolTip = function(date, pos, e, src) {
		if (this._tooltip) {
			if (this._tooltip.date.valueOf() == date.valueOf()) return;
			this._tooltip.innerHTML = "";
		} else {
			var t = this._tooltip = document.createElement("DIV");
			t.className = "dhx_tooltip";
			document.body.appendChild(t);
			t.onclick = scheduler._click.dhx_cal_data;

		}
		var evs = this.getEvents(date, this.date.add(date, 1, "day"));
		var html = "";

		for (var i = 0; i < evs.length; i++) {
			var ev = evs[i];
			var bg_color = (ev.color ? ("background-color:" + ev.color + ";") : "");
			var color = (ev.textColor ? ("color:" + ev.textColor + ";") : "");

			html += "<div class='dhx_tooltip_line' style='" + bg_color + "" + color + "' event_id='" + evs[i].id + "'>";
			html += "<div class='dhx_tooltip_date' style='" + bg_color + "" + color + "'>" + (evs[i]._timed ? this.templates.event_date(evs[i].start_date) : "") + "</div>";
			html += "<div class='dhx_event_icon icon_details'>&nbsp;</div>";
			html += this.templates.year_tooltip(evs[i].start_date, evs[i].end_date, evs[i]) + "</div>";
		}

		this._tooltip.style.display = "";
		this._tooltip.style.top = "0px";


		if (document.body.offsetWidth - pos.left - this._tooltip.offsetWidth < 0)
			this._tooltip.style.left = pos.left - this._tooltip.offsetWidth + "px";
		else
			this._tooltip.style.left = pos.left + src.offsetWidth + "px";

		this._tooltip.date = date;
		this._tooltip.innerHTML = html;

		if (document.body.offsetHeight - pos.top - this._tooltip.offsetHeight < 0)
			this._tooltip.style.top = pos.top - this._tooltip.offsetHeight + src.offsetHeight + "px";
		else
			this._tooltip.style.top = pos.top + "px";
	};

	scheduler._init_year_tooltip = function() {
		dhtmlxEvent(scheduler._els["dhx_cal_data"][0], "mouseover", function(e) {
			if (!is_year_mode()) return;

			var e = e || event;
			var src = e.target || e.srcElement;
			if (src.tagName.toLowerCase() == 'a') // fix for active links extension (it adds links to the date in the cell)
				src = src.parentNode;
			if ((src.className || "").indexOf("dhx_year_event") != -1)
				scheduler.showToolTip(from_attr(src.getAttribute("date")), getOffset(src), e, src);
			else
				scheduler.hideToolTip();
		});
		this._init_year_tooltip = function() {
		};
	};

	scheduler.attachEvent("onSchedulerResize", function() {
		if (is_year_mode()) {
			this.year_view(true);
			return false;
		}
		return true;
	});
	scheduler._get_year_cell = function(d) {
		//there can be more than 1 year in view
		//year can start not from January
		var m = d.getMonth() + 12 * (d.getFullYear() - this._min_date.getFullYear()) - this.week_starts._month;
		var t = this._els["dhx_cal_data"][0].childNodes[m];
		var d = this.week_starts[m] + d.getDate() - 1;


		return t.childNodes[2].firstChild.rows[Math.floor(d / 7)].cells[d % 7].firstChild;
	};

	var marked = [];
	scheduler._mark_year_date = function(d, ev) {
		var c = this._get_year_cell(d);
		c.className = "dhx_month_head dhx_year_event " + this.templates.event_class(ev.start_date, ev.end_date, ev);
		c.setAttribute("date", to_attr(d))
		marked.push(c);
	};
	scheduler._unmark_year_date = function(d) {
		this._get_year_cell(d).className = "dhx_month_head";
	};
	scheduler._year_render_event = function(ev) {
		var d = ev.start_date;
		if (d.valueOf() < this._min_date.valueOf())
			d = this._min_date;
		else d = this.date.date_part(new Date(d));

		while (d < ev.end_date) {
			this._mark_year_date(d, ev);
			d = this.date.add(d, 1, "day");
			if (d.valueOf() >= this._max_date.valueOf())
				return;
		}
	};

	scheduler.year_view = function(mode) {
		if (mode) {
			var temp = scheduler.xy.scale_height;
			scheduler.xy.scale_height = -1;
		}

		scheduler._els["dhx_cal_header"][0].style.display = mode ? "none" : "";
		scheduler.set_sizes();

		if (mode)
			scheduler.xy.scale_height = temp;


		scheduler._table_view = mode;
		if (this._load_mode && this._load()) return;

		if (mode) {
			scheduler._init_year_tooltip();
			scheduler._reset_year_scale();
			scheduler.render_view_data();
		} else {
			scheduler.hideToolTip();
		}
	};
	scheduler._reset_year_scale = function() {
		this._cols = [];
		this._colsS = {};
		var week_starts = []; //start day of first week in each month
		var b = this._els["dhx_cal_data"][0];

		var c = this.config;
		b.scrollTop = 0; //fix flickering in FF
		b.innerHTML = "";

		var dx = Math.floor(parseInt(b.style.width) / c.year_x);
		var dy = Math.floor((parseInt(b.style.height) - scheduler.xy.year_top) / c.year_y);
		if (dy < 190) {
			dy = 190;
			dx = Math.floor((parseInt(b.style.width) - scheduler.xy.scroll_width) / c.year_x);
		}

		var summ = dx - 11;
		var left = 0;
		var week_template = document.createElement("div");
		var dummy_date = this.date.week_start(new Date());
		for (var i = 0; i < 7; i++) {
			this._cols[i] = Math.floor(summ / (7 - i));
			this._render_x_header(i, left, dummy_date, week_template);
			dummy_date = this.date.add(dummy_date, 1, "day");
			summ -= this._cols[i];
			left += this._cols[i];
		}
		week_template.lastChild.className += " dhx_scale_bar_last";

		var sd = this.date[this._mode + "_start"](this.date.copy(this._date));
		var ssd = sd;

		for (var i = 0; i < c.year_y; i++)
			for (var j = 0; j < c.year_x; j++) {
				var d = document.createElement("DIV");
				d.style.cssText = "position:absolute;";
				d.setAttribute("date", this.templates.xml_format(sd));
				d.innerHTML = "<div class='dhx_year_month'></div><div class='dhx_year_week'>" + week_template.innerHTML + "</div><div class='dhx_year_body'></div>";
				d.childNodes[0].innerHTML = this.templates.year_month(sd);

				var dd = this.date.week_start(sd);
				var ed = this._reset_month_scale(d.childNodes[2], sd, dd);

				var r = d.childNodes[2].firstChild.rows;
				for (var k=r.length; k<6; k++) {
					r[0].parentNode.appendChild(r[0].cloneNode(true));
					for (var ri=0; ri < r[k].childNodes.length; ri++) {
					   r[k].childNodes[ri].className = "dhx_after";
					   r[k].childNodes[ri].firstChild.innerHTML = scheduler.templates.month_day(ed);
					   ed = scheduler.date.add(ed,1,"day");
					}
				}
				b.appendChild(d);

				d.childNodes[1].style.height = d.childNodes[1].childNodes[0].offsetHeight + "px"; // dhx_year_week should have height property so that day dates would get correct position. dhx_year_week height = height of it's child (with the day name)
				var dt = Math.round((dy - 190) / 2);
				d.style.marginTop = dt + "px";
				this.set_xy(d, dx - 10, dy - dt - 10, dx * j + 5, dy * i + 5 + scheduler.xy.year_top);

				week_starts[i * c.year_x + j] = (sd.getDay() - (this.config.start_on_monday ? 1 : 0) + 7) % 7;
				sd = this.date.add(sd, 1, "month");

			}
		this._els["dhx_cal_date"][0].innerHTML = this.templates[this._mode + "_date"](ssd, sd, this._mode);
		this.week_starts = week_starts;
		week_starts._month = ssd.getMonth();
		this._min_date = ssd;
		this._max_date = sd;
	}

})();
