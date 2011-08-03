/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
window.dhtmlXTooltip={};

dhtmlXTooltip.config = {
	className: 'dhtmlXTooltip tooltip',
	timeout_to_display: 50,
	delta_x: 15,
	delta_y: -20
};

dhtmlXTooltip.tooltip = document.createElement('div');
dhtmlXTooltip.tooltip.className = dhtmlXTooltip.config.className;

dhtmlXTooltip.show = function(event, text) { //browser event, text to display
    var dhxTooltip = dhtmlXTooltip;
    var tooltip_div = this.tooltip;
    var tooltip_div_style = tooltip_div.style;
	dhxTooltip.tooltip.className = dhxTooltip.config.className;
	var pos=this.position(event);
	
	var target = event.target||event.srcElement;
	if (this.isTooltip(target)) {return;} // if we are over tooltip -- do nothing, just return (so tooltip won't move)
	
	var offsetleft = 0;
    var offsettop = 0;
	var pobj = scheduler._obj;
	if(pobj.offsetParent) {
		do {
			offsetleft += pobj.offsetLeft;
			offsettop += pobj.offsetTop;
		} while (pobj = pobj.offsetParent);
	}
	
	var actual_x = pos.x + (dhxTooltip.config.delta_x||0) - offsetleft;
	var actual_y = pos.y - (dhxTooltip.config.delta_y||0) - offsettop;
	
	tooltip_div_style.visibility = "hidden";
	
	if(tooltip_div_style.removeAttribute) {
		tooltip_div_style.removeAttribute("right");
		tooltip_div_style.removeAttribute("bottom");
	} else {
		tooltip_div_style.removeProperty("right");
		tooltip_div_style.removeProperty("bottom");
	}

	tooltip_div_style.left = "0";
	tooltip_div_style.top = "0";
	
	this.tooltip.innerHTML = text;
	scheduler._obj.appendChild(this.tooltip);
	
	var tooltip_width = this.tooltip.offsetWidth;
	var tooltip_height = this.tooltip.offsetHeight;

	if ((scheduler._obj.offsetWidth - actual_x - (scheduler.xy.margin_left||0) - tooltip_width) < 0) { // tooltip is out of the right page bound
		if(tooltip_div_style.removeAttribute)
			tooltip_div_style.removeAttribute("left");
		else
			tooltip_div_style.removeProperty("left");
		tooltip_div_style.right = (scheduler._obj.offsetWidth - actual_x + 2 * (dhxTooltip.config.delta_x||0)) + "px";
	} else {
		if (actual_x < 0) { // tooltips is out of the left page bound
			tooltip_div_style.left = (pos.x + Math.abs(dhxTooltip.config.delta_x||0)) + "px";
		} else { // normal situation
			tooltip_div_style.left = actual_x + "px";
		}
	}

	if ((scheduler._obj.offsetHeight - actual_y - (scheduler.xy.margin_top||0) - tooltip_height) < 0) { // tooltip is below bottom of the page
		if(tooltip_div_style.removeAttribute)
			tooltip_div_style.removeAttribute("top");
		else
			tooltip_div_style.removeProperty("top");
		tooltip_div_style.bottom = (scheduler._obj.offsetHeight - actual_y - 2 * (dhxTooltip.config.delta_y||0)) + "px";
	} else {
		if (actual_y < 0) { // tooltip is higher then top of the page
			tooltip_div_style.top = (pos.y + Math.abs(dhxTooltip.config.delta_y||0)) + "px";
		}
		else { // normal situation
			tooltip_div_style.top = actual_y + "px";
		}
	}
	
	tooltip_div_style.visibility = "visible";
};

dhtmlXTooltip.hide = function() {
	if(this.tooltip.parentNode) {
		this.tooltip.parentNode.removeChild(this.tooltip);
	}
};
dhtmlXTooltip.delay = function(method, object, params, delay) {
	if(this.tooltip._timeout_id) {
		window.clearTimeout(this.tooltip._timeout_id);
	}
	this.tooltip._timeout_id = setTimeout(function(){
		var ret = method.apply(object,params);
		method = object = params = null;
		return ret;
	},delay||this.config.timeout_to_display);	
};

dhtmlXTooltip.isTooltip = function(node){
	var res = false;
	while (node && !res) {
		res = (node.className == this.tooltip.className);
		node=node.parentNode;
	}
	return res;
};

dhtmlXTooltip.position = function(ev) {
   ev = ev || window.event;
   if(ev.pageX || ev.pageY) //FF, KHTML
      return {x:ev.pageX, y:ev.pageY};
   //IE
   var d  =  ((dhtmlx._isIE)&&(document.compatMode != "BackCompat"))?document.documentElement:document.body;
   return {
      x:ev.clientX + d.scrollLeft - d.clientLeft,
      y:ev.clientY + d.scrollTop  - d.clientTop
   };
};

scheduler.attachEvent("onMouseMove", function(event_id, e){ // (scheduler event_id, browser event)
	var ev = window.event||e;
	var target = ev.target||ev.srcElement;
    var dhxTooltip = dhtmlXTooltip;

	if (event_id || dhxTooltip.isTooltip(target)) { // if we are over event or tooltip
		var event = scheduler.getEvent(event_id) || scheduler.getEvent(dhxTooltip.tooltip.event_id);
		if(!event)
			return;
		dhxTooltip.tooltip.event_id = event.id;
		var text = scheduler.templates.tooltip_text(event.start_date, event.end_date, event);
		
        var evt = undefined;
        if (_isIE) { //make a copy of event, will be used in timed call
            evt = document.createEventObject(ev);
		}

		dhxTooltip.delay(dhxTooltip.show, dhxTooltip, [(evt||ev), text]); // showing tooltip
	} else {
		dhxTooltip.delay(dhxTooltip.hide, dhxTooltip, []);
	}
});
scheduler.attachEvent("onBeforeDrag", function(){
    dhtmlXTooltip.hide();
    return true;
});

/* Could be redifined */
scheduler.templates.tooltip_date_format=scheduler.date.date_to_str("%Y-%m-%d %H:%i"); 

scheduler.templates.tooltip_text = function(start,end,event) {
	return "<b>Event:</b> "+event.text+"<br/><b>Start date:</b> "+scheduler.templates.tooltip_date_format(start)+"<br/><b>End date:</b> "+scheduler.templates.tooltip_date_format(end);
};
