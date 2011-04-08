window.dhtmlXTooltip={version:0.1};

dhtmlXTooltip.config = {
	className: 'dhtmlXTooltip tooltip',
	timeout_to_display: 50,
	delta_x: 15,
	delta_y: -20
};

dhtmlXTooltip.tooltip = document.createElement('div');
dhtmlXTooltip.tooltip.className = dhtmlXTooltip.config.className;

dhtmlXTooltip.show = function(event, text) { //browser event, text to display
	dhtmlXTooltip.tooltip.className = dhtmlXTooltip.config.className;
	var pos=this.position(event);

	var target = event.target||event.srcElement;
	if (this.isTooltip(target)) {return;} // if we are over tooltip -- do nothing, just return (so tooltip won't move)
	
	var actual_x = pos.x+dhtmlXTooltip.config.delta_x||0;
	var actual_y = pos.y-dhtmlXTooltip.config.delta_y||0;
	
	this.tooltip.style.visibility = "hidden";
	
	if(this.tooltip.style.removeAttribute) {
		this.tooltip.style.removeAttribute("right");
		this.tooltip.style.removeAttribute("bottom");	
	} else {
		this.tooltip.style.removeProperty("right");
		this.tooltip.style.removeProperty("bottom");		
	}

	this.tooltip.style.left = "0px";
	this.tooltip.style.top = "0px";	
	
	this.tooltip.innerHTML = text;
	scheduler._obj.appendChild(this.tooltip);
	
	var tooltip_width = this.tooltip.offsetWidth;
	var tooltip_height = this.tooltip.offsetHeight;
	
	if (document.body.offsetWidth - actual_x - tooltip_width < 0) { // tooltip is out of the right page bound
		if(this.tooltip.style.removeAttribute) 
			this.tooltip.style.removeAttribute("left");
		else
			this.tooltip.style.removeProperty("left");
		this.tooltip.style.right = (document.body.offsetWidth - actual_x + 2 * dhtmlXTooltip.config.delta_x||0) + "px";
	} else {
		if (actual_x < 0) { // tooltips is out of the left page bound
			this.tooltip.style.left = (pos.x + Math.abs(dhtmlXTooltip.config.delta_x||0)) + "px"; 
		} else { // normal situation
			this.tooltip.style.left = actual_x + "px";
		}
	}
	
	if (document.body.offsetHeight - actual_y - tooltip_height < 0) { // tooltip is below bottom of the page
		if(this.tooltip.style.removeAttribute) 
			this.tooltip.style.removeAttribute("top");
		else
			this.tooltip.style.removeProperty("top");
		this.tooltip.style.bottom = (document.body.offsetHeight - actual_y - 2 * dhtmlXTooltip.config.delta_y||0) + "px";
	} else {
		if (actual_y < 0) { // tooltip is higher then top of the page
			this.tooltip.style.top = (pos.y + Math.abs(dhtmlXTooltip.config.delta_y||0)) + "px"; 
		}
		else { // normal situation
			this.tooltip.style.top = actual_y + "px";
		}
	}
	
	this.tooltip.style.visibility = "visible";
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
		method = obj = params = null;
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
   var ev = ev || window.event;
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
	var ev = e||window.event;
	var target = ev.target||ev.srcElement;

	if (event_id || dhtmlXTooltip.isTooltip(target)) { // if we are over event or tooltip
		var event = scheduler.getEvent(event_id) || scheduler.getEvent(dhtmlXTooltip.tooltip.event_id);
		dhtmlXTooltip.tooltip.event_id = event.id;
		var text = scheduler.templates.tooltip_text(event.start_date, event.end_date, event);
		
		if (_isIE) { //make a copy of event, will be used in timed call
			var evt = document.createEventObject(ev);
		}
		
		dhtmlXTooltip.delay(dhtmlXTooltip.show, dhtmlXTooltip, [ evt||ev , text]); // showing tooltip
	} else {
		dhtmlXTooltip.delay(dhtmlXTooltip.hide, dhtmlXTooltip, []);
	}
});

/* Could be redifined */
scheduler.templates.tooltip_text = function(start,end,event) {
	return "<b>Event:</b> "+event.text+"<br/><b>Start date:</b> "+scheduler.templates.tooltip_date_format(start)+"<br/><b>End date:</b> "+scheduler.templates.tooltip_date_format(end);
};