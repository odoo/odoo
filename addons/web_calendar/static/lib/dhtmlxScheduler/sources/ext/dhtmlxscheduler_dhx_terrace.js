/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){

	scheduler.config.fix_tab_position = true;
	scheduler.config.use_select_menu_space = true;
	scheduler.config.hour_size_px = 44;
	scheduler.xy.nav_height = 59;
	scheduler.xy.bar_height = 24;
	scheduler.config.wide_form = true;
	scheduler.xy.lightbox_additional_height = 90;

	scheduler.config.displayed_event_color = "#ff4a4a";
	scheduler.config.displayed_event_text_color = "#ffef80";

	scheduler.templates.event_bar_date = function(start,end,ev) {
		return "• <b>"+scheduler.templates.event_date(start)+"</b> ";
	};

	scheduler.attachEvent("onLightbox", function(){
		var lightbox = scheduler.getLightbox();
		var divs = lightbox.getElementsByTagName('div');
		for (var i=0; i<divs.length; i++) {
			var div = divs[i];
			if (div.className == "dhx_close_icon") {
				div.onclick = function() {
					scheduler.endLightbox(false, lightbox);
				};
				break;
			}
		}
	});

	scheduler._lightbox_template="<div class='dhx_cal_ltitle'><span class='dhx_mark'>&nbsp;</span><span class='dhx_time'></span><span class='dhx_title'></span><div class='dhx_close_icon'></div></div><div class='dhx_cal_larea'></div>";

	scheduler.attachEvent("onTemplatesReady", function() {

		var date_to_str = scheduler.date.date_to_str("%d");
		var old_month_day = scheduler.templates.month_day;
		scheduler.templates.month_day = function(date) {
			if (this._mode == "month") {
				var label = date_to_str(date);
				if (date.getDate() == 1) {
					label = scheduler.locale.date.month_full[date.getMonth()] + " " + label;
				}
				if (+date == +scheduler.date.date_part(new Date)) {
					label = scheduler.locale.labels.dhx_cal_today_button + " " + label;
				}
				return label;
			} else {
				return old_month_day.call(this, date);
			}
		};

		if (scheduler.config.fix_tab_position){
			var navline_divs = scheduler._els["dhx_cal_navline"][0].getElementsByTagName('div');
			var tabs = [];
			var last = 211;
			for (var i=0; i<navline_divs.length; i++) {
				var div = navline_divs[i];
				var name = div.getAttribute("name");
				if (name) { // mode tab
					div.style.right = "auto";
					switch (name) {
						case "day_tab":
							div.style.left = "14px";
							div.className += " dhx_cal_tab_first";
							break;
						case "week_tab":
							div.style.left = "75px";
							break;
						case "month_tab":
							div.style.left = "136px";
							div.className += " dhx_cal_tab_last";
							break;
						default:
							div.style.left = last+"px";
							div.className += " dhx_cal_tab_standalone";
							last = last + 14 + div.offsetWidth;
					}
				}

			}
		}
	});

})();

