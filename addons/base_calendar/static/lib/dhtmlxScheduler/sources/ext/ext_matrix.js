(function(){
scheduler.matrix = {};
scheduler._merge=function(a,b){
	for (var c in b)
		if (typeof a[c] == "undefined")
			a[c]=b[c];
};
scheduler.createTimelineView=function(obj){

	
	scheduler._merge(obj,{
		section_autoheight: true,
		name:"matrix",
		x:"time",
		y:"time",
		x_step:1,
		x_unit:"hour",
		y_unit:"day",
		y_step:1,
		x_start:0,
		x_size:24,
		y_start:0,
		y_size:	7,
		render:"cell",
		dx:200,
		dy:50,
		_logic: function(render_name, y_unit, timeline) {
			var res = {};
			if(scheduler.checkEvent("onBeforeViewRender")) { 
				res = scheduler.callEvent("onBeforeViewRender", [render_name, y_unit, timeline]);
			}
			return res;
		}
	});
	
	if (scheduler.checkEvent("onTimelineCreated")) { 
		scheduler.callEvent("onTimelineCreated", [obj]);
	}

	//init custom wrappers
	scheduler[obj.name+"_view"]=function(){
		scheduler.renderMatrix.apply(obj, arguments);
	};
	
	var old = scheduler.render_data;
	scheduler.render_data=function(evs, mode){
		if (this._mode == obj.name){
			if (mode)	//repaint single event, precision is not necessary
				for (var i=0; i < evs.length; i++) {
					this.clear_event(evs[i]);
					this.render_timeline_event.call(this.matrix[this._mode], evs[i], 0, true);
				}
			else
   			set_full_view.call(obj,true);
   		} else
   			return old.apply(this,arguments);
	};
	
	scheduler.matrix[obj.name]=obj;
	scheduler.templates[obj.name+"_cell_value"] = function(ar){ return ar?ar.length:""; };
	scheduler.templates[obj.name+"_cell_class"] = function(ar){ return ""; };
	scheduler.templates[obj.name+"_scalex_class"] = function(ar){ return ""; };
	
	scheduler.templates[obj.name+"_scaley_class"] = function(section_id, section_label, section_options){ return "class"; };
	scheduler.templates[obj.name+"_scale_label"] = function(section_id, section_label, section_options){ return section_label; };
	
	scheduler.templates[obj.name+"_tooltip"] = function(a,b,e){ return e.text; };
	scheduler.templates[obj.name+"_date"] = function(datea, dateb){ 
		if (datea.getDay()==dateb.getDay() && datea-dateb<(24*60*60*1000))
			return scheduler.templates.day_date(datea);
		return scheduler.templates.week_date(datea, dateb); 
	};
	
	scheduler.templates[obj.name+"_scale_date"] = scheduler.date.date_to_str(obj.x_date||scheduler.config.hour_date);
		
	scheduler.date["add_"+obj.name]=function(a,b,c){
		return scheduler.date.add(a,(obj.x_length||obj.x_size)*b*obj.x_step,obj.x_unit);
	};
	
	// note this is not correct start_date as it doesn't take into account x_start value (though scheduler._min_date is correct)
	scheduler.date[obj.name+"_start"] = scheduler.date[obj.x_unit+"_start"] || scheduler.date.day_start;
	
	scheduler.attachEvent("onSchedulerResize",function(){
		if (this._mode == obj.name){
			set_full_view.call(obj,true);
			return false;
		}
		return true;
	});
	
	scheduler.attachEvent("onOptionsLoad",function(){
			obj.order = {};
			for(var i=0; i<obj.y_unit.length;i++)
				obj.order[obj.y_unit[i].key]=i;
			if(obj.name == scheduler._mode) {
				if (scheduler._date) 
					scheduler.setCurrentView(scheduler._date, scheduler._mode);
			}
	});	
	scheduler.callEvent("onOptionsLoad",[obj]);
	
	//enable drag for non-cell modes
		if (obj.render != "cell"){
		var temp_date = new Date();
		var step_diff = (scheduler.date.add(temp_date, 1, obj.x_unit).valueOf() - temp_date.valueOf());
		scheduler["mouse_"+obj.name]=function(pos){	//mouse_coord handler
			//get event object
			var ev = this._drag_event;
			if (this._drag_id){
				ev = this.getEvent(this._drag_id);
				this._drag_event._dhx_changed = true;
			}
			pos.x-=obj.dx;
			//scheduler.date.date_part(ev.start_date);
			
			var summ = 0, xind = 0, yind = 0;  
			for (xind; xind < this._cols.length-1; xind++) { 
				summ+=this._cols[xind];
				if (summ>pos.x){ //index of section
					break;
				}
			}
			
			summ = 0;
			for (yind; yind < this._colsS.heights.length; yind++) {
				summ+=this._colsS.heights[yind];
				if (summ>pos.y)
					break;
			}
			
			pos.fields={};
			pos.fields[obj.y_property] = ev[obj.y_property] = obj.y_unit[yind].key;
			
			pos.x =  yind/10000000; //force rendering when section changes
			
			if (this._drag_mode == "new-size" && ev.start_date*1==this._drag_start*1) {
				xind++;
			}
				
			
			if(xind >= obj._trace_x.length) { // if our event is at the end of the view
				var end_date = scheduler.date.add(obj._trace_x[obj._trace_x.length-1], obj.x_step, obj.x_unit);
			} else {
				var end_date = obj._trace_x[xind];
			}

			pos.y = Math.round((end_date-this._min_date)/(1000*60*this.config.time_step));
			pos.custom = true;
			pos.shift = step_diff;

			return pos;
		};
	}
};

scheduler.render_timeline_event = function(ev, stack, attach){

	var x_start = _getX(ev, false, this._step);
	var x_end = _getX(ev, true, this._step);

	var hb = scheduler.xy.bar_height;
	var y = 2+stack*hb; 
					
				
	var cs = scheduler.templates.event_class(ev.start_date,ev.end_date,ev);
	cs = "dhx_cal_event_line "+(cs||"");
		
	var html='<div event_id="'+ev.id+'" class="'+cs+'" style="position:absolute; top:'+y+'px; left:'+x_start+'px; width:'+Math.max(0,x_end-x_start)+'px;'+(ev._text_style||"")+'">'+scheduler.templates.event_bar_text(ev.start_date,ev.end_date,ev)+'</div>';
	
	if (!attach) 
		return html;
	else {
		var d = document.createElement("DIV");
		d.innerHTML = html;
		
		var ind = this.order[ev[this.y_property]];
		var parent = scheduler._els["dhx_cal_data"][0].firstChild.rows[ind].cells[1].firstChild;
		
		scheduler._rendered.push(d.firstChild);
		parent.appendChild(d.firstChild);
	}

};
	
function trace_events(){
	//minimize event set
	var evs = scheduler.getEvents(scheduler._min_date, scheduler._max_date);
	var matrix =[];
	for (var i=0; i < this.y_unit.length; i++) 
		matrix[i]=[];
	
		
	//next code defines row for undefined key
	//most possible it is an artifact of incorrect configuration
	if (!matrix[y])
		matrix[y]=[];
	
	for (var i=0; i < evs.length; i++) {
		var y = this.order[evs[i][this.y_property]];
		var x = 0; 
		while (this._trace_x[x+1] && evs[i].start_date>=this._trace_x[x+1]) x++;
		while (this._trace_x[x] && evs[i].end_date>this._trace_x[x]) {
			if (!matrix[y][x]) matrix[y][x]=[];
			matrix[y][x].push(evs[i]);
			x++;
		}
	}
	return matrix;
}

// function used to get X (both start and end) coordinates for timeline bar view
function _getX(ev, isEndPoint, step) {
	var x = 0;
	var date = (isEndPoint) ? ev.end_date : ev.start_date;
	if(date.valueOf()>scheduler._max_date.valueOf())
		date = scheduler._max_date;
	var delta = date - scheduler._min_date_timeline;
	if (delta<0) {
		column_offset = 0;
	} else {
		var index = Math.round( delta/(step*scheduler._cols[0]) ); // results varies ~0.9 - ~24.17, e.g. that way we get 1 and 24
		if(index>scheduler._cols.length) // if columns really small it's possible to get incorrect index
			index = scheduler._cols.length;
		for (var k=0; k<index; k++) {
			x += scheduler._cols[k];
		}
		var column_date = scheduler.date.add(scheduler._min_date_timeline, scheduler.matrix[scheduler._mode].x_step*index, scheduler.matrix[scheduler._mode].x_unit);
		delta = date - column_date;
		var column_offset = Math.floor(delta/step);
	}
	x += (isEndPoint) ? column_offset-14 : column_offset+1;
	return x;
}
	

function y_scale(d){ 

	var html = "<table style='table-layout:fixed;' cellspacing='0' cellpadding='0'>";
	var evs=[];
	if (scheduler._load_mode && scheduler._load()) return;
	if (this.render == "cell")
		evs = trace_events.call(this);
	else {
		var tevs = scheduler.getEvents(scheduler._min_date, scheduler._max_date);
		for (var j=0; j<tevs.length; j++){
			var ind =  this.order[ tevs[j][this.y_property] ];
			if (!evs[ind]) evs[ind] = [];
			evs[ind].push(tevs[j]);
		}
	}
		
	var summ = 0; 
	for (var i=0; i < scheduler._cols.length; i++)
		summ+=scheduler._cols[i];
		
	var step = new Date();
	step = (scheduler.date.add(step, this.x_step*this.x_size, this.x_unit)-step)/summ;
	
	this._step = step;
	this._summ = summ;
	
	var heights = scheduler._colsS.heights=[]; 
	
	
	for (var i=0; i<this.y_unit.length; i++){
		
		var stats = this._logic(this.render, this.y_unit[i], this); // obj with custom style
		
		scheduler._merge(stats, {
			height: this.dy
		});
		
		//autosize height, if we have a free space
		if(this.section_autoheight) {
			if (this.y_unit.length * stats.height < d.offsetHeight) {
				stats.height = Math.max(stats.height, Math.floor((d.offsetHeight - 1) / this.y_unit.length));
			}
		}	
				
		scheduler._merge(stats, {
			//section 1
			tr_className: "",
			style_height: "height:"+stats.height+"px;",
			style_width: "width:"+(this.dx-1)+"px;",
			td_className: "dhx_matrix_scell "+scheduler.templates[this.name+"_scaley_class"](this.y_unit[i].key, this.y_unit[i].label, this),
			td_content: scheduler.templates[this.name+'_scale_label'](this.y_unit[i].key, this.y_unit[i].label, this),
			//section 2
			summ_width: "width:"+summ+"px;",
			//section 3
			table_className: ''
		});
		
		// section 1
		html+="<tr class='"+stats.tr_className+"' style='"+stats.style_height+"'><td class='"+stats.td_className+"' style='"+stats.style_width+"'>"+stats.td_content+"</td>";	

		if (this.render == "cell"){
			for (var j=0; j < scheduler._cols.length; j++) {
					html+="<td class='dhx_matrix_cell "+scheduler.templates[this.name+"_cell_class"](evs[i][j],this._trace_x[j],this.y_unit[i])+"' style='width:"+(scheduler._cols[j]-1)+"px'><div style='width:"+(scheduler._cols[j]-1)+"px'>"+scheduler.templates[this.name+"_cell_value"](evs[i][j])+"<div></td>";
			}
		} else {
			//section 2
			html+="<td><div style='"+stats.summ_width+" "+stats.style_height+" position:relative;' class='dhx_matrix_line'>";

			if (evs[i]){
				evs[i].sort(function(a,b){ return a.start_date>b.start_date?1:-1; });
				var stack=[]; 
				for (var j=0; j<evs[i].length; j++){
					var ev = evs[i][j];

					//get line in stack
					var stack_pointer = 0;
					
					while (stack[stack_pointer] && stack[stack_pointer].end_date > ev.start_date)
						stack_pointer++;
					stack[stack_pointer]=ev;
					//render line
					
					html+=scheduler.render_timeline_event.call(this, ev, stack_pointer);
				}
			}
			//section 3
				html+="<table class='"+stats.table_className+"' cellpadding='0' cellspacing='0' style='"+stats.summ_width+" "+stats.style_height+"' >";
			for (var j=0; j < scheduler._cols.length; j++)
				html+="<td class='dhx_matrix_cell "+scheduler.templates[this.name+"_cell_class"](evs[i],this._trace_x[j],this.y_unit[i])+"' style='width:"+(scheduler._cols[j]-1)+"px'><div style='width:"+(scheduler._cols[j]-1)+"px'><div></td>";
			html+="</table>";			
			html+="</div></td>";	
		}
		html+="</tr>";
	}
	html += "</table>";
	this._matrix = evs;
	d.scrollTop = 0; //fix flickering in FF
	d.innerHTML = html;
	
	scheduler._rendered = [];
	var divs = document.getElementsByTagName("DIV");
	for (var i=0; i < divs.length; i++)
		if (divs[i].getAttribute("event_id"))
			scheduler._rendered.push(divs[i]);
			
	for (var i=0; i < d.firstChild.rows.length; i++)
		heights.push(d.firstChild.rows[i].offsetHeight); 
	
}
function x_scale(h){
	h.innerHTML = "<div></div>"; h=h.firstChild;
	
	scheduler._cols=[];	//store for data section
	scheduler._colsS={height:0};
	this._trace_x =[];
	
	scheduler._min_date_timeline = scheduler._min_date; 
		
	var start = scheduler._min_date;
	var summ = scheduler._x-this.dx-18; //border delta

	var left = this.dx;
	
	for (var i=0; i<this.x_size; i++){
		scheduler._cols[i]=Math.floor(summ/(this.x_size-i));
		this._trace_x[i]=new Date(start);
		
		scheduler._render_x_header(i, left, start, h);
		
		var cs = scheduler.templates[this.name+"_scalex_class"](start);
		if (cs)	
			h.lastChild.className += " "+cs;
			
		start = scheduler.date.add(start, this.x_step, this.x_unit);
		
		summ-=scheduler._cols[i];
		left+=scheduler._cols[i];
	}
	
	var trace = this._trace_x;
	h.onclick = function(e){
		var pos = locate_hcell(e);
		if (pos)
			scheduler.callEvent("onXScaleClick",[pos.x, trace[pos.x], e||event]);
	};
	h.ondblclick = function(e){
		var pos = locate_hcell(e);
		if (pos)
			scheduler.callEvent("onXScaleDblClick",[pos.x, trace[pos.x], e||event]);
	};
}
function set_full_view(mode){
	if (mode){	
		scheduler.set_sizes();
		_init_matrix_tooltip();
		//we need to have day-rounded scales for navigation
		//in same time, during rendering scales may be shifted
		var temp = scheduler._min_date;
			x_scale.call(this,scheduler._els["dhx_cal_header"][0]);
			y_scale.call(this,scheduler._els["dhx_cal_data"][0]);
		scheduler._min_date = temp;
		scheduler._els["dhx_cal_date"][0].innerHTML=scheduler.templates[this.name+"_date"](scheduler._min_date, scheduler._max_date);
		scheduler._table_view=true;
	}
}


function hideToolTip(){ 
	if (scheduler._tooltip){
		scheduler._tooltip.style.display = "none";
		scheduler._tooltip.date = "";
	}
}
function showToolTip(obj,pos,offset){ 
	if (obj.render != "cell") return;
	var mark = pos.x+"_"+pos.y;		
	var evs = obj._matrix[pos.y][pos.x];
	
	if (!evs) return hideToolTip();
	
	evs.sort(function(a,b){ return a.start_date>b.start_date?1:-1; });

	if (scheduler._tooltip){
		if (scheduler._tooltip.date == mark) return;
		scheduler._tooltip.innerHTML="";
	} else {
		var t = scheduler._tooltip = document.createElement("DIV");
		t.className = "dhx_tooltip";
		document.body.appendChild(t);
		t.onclick = scheduler._click.dhx_cal_data;
	}
	
	var html = "";
   
	for (var i=0; i<evs.length; i++){
		html+="<div class='dhx_tooltip_line' event_id='"+evs[i].id+"'>";
		html+="<div class='dhx_tooltip_date'>"+(evs[i]._timed?scheduler.templates.event_date(evs[i].start_date):"")+"</div>";
		html+="<div class='dhx_event_icon icon_details'>&nbsp;</div>";
		html+=scheduler.templates[obj.name+"_tooltip"](evs[i].start_date, evs[i].end_date,evs[i])+"</div>";
   }
   
	scheduler._tooltip.style.display="";   
	scheduler._tooltip.style.top = "0px";
   
	if (document.body.offsetWidth-offset.left-scheduler._tooltip.offsetWidth < 0)
		scheduler._tooltip.style.left = offset.left-scheduler._tooltip.offsetWidth+"px";
	else
		scheduler._tooltip.style.left = offset.left+pos.src.offsetWidth+"px";
      
	scheduler._tooltip.date = mark;
	scheduler._tooltip.innerHTML = html;
   
	if (document.body.offsetHeight-offset.top-scheduler._tooltip.offsetHeight < 0)
		scheduler._tooltip.style.top= offset.top-scheduler._tooltip.offsetHeight+pos.src.offsetHeight+"px";
	else
		scheduler._tooltip.style.top= offset.top+"px";
}

function _init_matrix_tooltip(){
	dhtmlxEvent(scheduler._els["dhx_cal_data"][0], "mouseover", function(e){
		var obj = scheduler.matrix[scheduler._mode];
		if (obj){
			var pos = scheduler._locate_cell_timeline(e);
			var e = e || event;
			var src = e.target||e.srcElement;
			if (pos)
				return showToolTip(obj,pos,getOffset(pos.src));
		}
		hideToolTip();
	});
   _init_matrix_tooltip=function(){};
}

scheduler.renderMatrix = function(mode){
	var start_date = scheduler.date[this.name+"_start"](scheduler._date);
	scheduler._min_date = scheduler.date.add(start_date, this.x_start*this.x_step, this.x_unit);
	scheduler._max_date = scheduler.date.add(scheduler._min_date, this.x_size*this.x_step, this.x_unit);
	scheduler._table_view = true;
	set_full_view.call(this,mode);
};

function html_index(el) {
	var p = el.parentNode.childNodes;
	for (var i=0; i < p.length; i++) 
		if (p[i] == el) return i;
	return -1;
}
function locate_hcell(e){
	e = e||event;
	var trg = e.target?e.target:e.srcElement;
	while (trg && trg.tagName != "DIV")
		trg=trg.parentNode;
	if (trg && trg.tagName == "DIV"){
		var cs = trg.className.split(" ")[0];
		if (cs == "dhx_scale_bar")
			return { x:html_index(trg), y:-1, src:trg, scale:true };
	}
}
scheduler._locate_cell_timeline = function(e){
	e = e||event;
	var trg = e.target?e.target:e.srcElement;
	while (trg && trg.tagName != "TD")
		trg=trg.parentNode;
	if (trg && trg.tagName == "TD"){
		var cs = trg.className.split(" ")[0];
		if (cs == "dhx_matrix_cell") {
		
			if(scheduler._isRender("cell")) {
				return { x:trg.cellIndex-1, y:trg.parentNode.rowIndex, src:trg };
                        } else { // probably desired path for all modes except cell
				var trscell = trg.parentNode; // moving out from current td
				while(trscell && trscell.tagName != "TD") { 
					trscell=trscell.parentNode;
				}
				return { x:trg.cellIndex, y:trscell.parentNode.rowIndex, src:trg };
			}
		}
		else if (cs == "dhx_matrix_scell")
			return { x:-1, y:trg.parentNode.rowIndex, src:trg, scale:true };
	}
	return false;
};

var old_click = scheduler._click.dhx_cal_data;
scheduler._click.dhx_cal_data = function(e){
	var ret = old_click.apply(this,arguments);
	var obj = scheduler.matrix[scheduler._mode];
	if (obj){
		var pos = scheduler._locate_cell_timeline(e);
		if (pos){
			if (pos.scale)
				scheduler.callEvent("onYScaleClick",[pos.y, obj.y_unit[pos.y], e||event]);
			else
				scheduler.callEvent("onCellClick",[pos.x, pos.y, obj._trace_x[pos.x], (((obj._matrix[pos.y]||{})[pos.x])||[]), e||event]);
		}
	}
	return ret;
};

scheduler.dblclick_dhx_matrix_cell = function(e){
	var obj = scheduler.matrix[scheduler._mode];
	if (obj){
		var pos = scheduler._locate_cell_timeline(e);
		if (pos){
			if (pos.scale)
				scheduler.callEvent("onYScaleDblClick",[pos.y, obj.y_unit[pos.y], e||event]);
			else
				scheduler.callEvent("onCellDblClick",[pos.x, pos.y, obj._trace_x[pos.x], (((obj._matrix[pos.y]||{})[pos.x])||[]), e||event]);
		}
	}
};
scheduler.dblclick_dhx_matrix_scell = function(e){
	return scheduler.dblclick_dhx_matrix_cell(e);
};

scheduler._isRender = function(mode){
	return (scheduler.matrix[scheduler._mode] && scheduler.matrix[scheduler._mode].render == mode);
};

scheduler.attachEvent("onCellDblClick", function (x, y, a, b, event){
	if (this.config.readonly|| (event.type == "dblclick" && !this.config.dblclick_create)) return;
	
	var obj = scheduler.matrix[scheduler._mode];
	var event_options = {};
	event_options['start_date'] = obj._trace_x[x];
	event_options['end_date'] = (obj._trace_x[x+1]) ? obj._trace_x[x+1] : scheduler.date.add(obj._trace_x[x], obj.x_step, obj.x_unit);
	event_options[scheduler.matrix[scheduler._mode].y_property] = obj.y_unit[y].key;
	scheduler.addEventNow(event_options, null, event);
});	

scheduler.attachEvent("onBeforeDrag", function (event_id, mode, native_event_object){
	if(scheduler._isRender("cell")) {
		return false;
	}
	return true;
});	

})();