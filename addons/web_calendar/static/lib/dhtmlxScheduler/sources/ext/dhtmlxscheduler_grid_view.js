/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){
	scheduler.grid = {
		sort_rules:{
			"int":function(a,b, getVal){ return getVal(a)*1 < getVal(b)*1?1:-1},
			"str":function(a,b, getVal){ return getVal(a) < getVal(b)?1:-1},
			"date":function(a,b, getVal){ return new Date(getVal(a))< new Date(getVal(b))?1:-1}
		},
		_getObjName:function(name){
			return "grid_"+name;
		},
		_getViewName:function(objName){
			return objName.replace(/^grid_/,'');
		}
	};
}
)();
/*
obj={
    name:'grid_name'
	fields:[
                  { id:"id", label:"Id", width:80, sort:"int/date/str", template:function(start_date, end_date, ev){ return ""}, align:"right/left/center" },
                  { id:"text", label:"Text", width:'*', css:"class_name", sort:function(a,b){ return 1 or -1}, valign:'top/bottom/middle' }
                  ...
            ],
	from:new Date(0),
	to:Date:new Date(9999,1,1),
	rowHeight:int,
	paging:true/false,
	select:true/false
}
*/


scheduler.createGridView=function(obj){

	var name = obj.name || 'grid';
	var objName = scheduler.grid._getObjName(name);

	scheduler.config[name + '_start'] = obj.from ||(new Date(0));
	scheduler.config[name + '_end'] = obj.to || (new Date(9999,1,1));

	scheduler[objName] = obj;
	scheduler[objName].defPadding = 8;
	scheduler[objName].columns = scheduler[objName].fields;
	delete scheduler[objName].fields;
	function isValidSize(size){
		return !(size !== undefined && (size*1 != size || size < 0));
	}

	var cols = scheduler[objName].columns;
	for(var i=0; i < cols.length; i++){
		if(isValidSize(cols[i].width))
			cols[i].initialWidth = cols[i].width;
		if(!isValidSize(cols[i].paddingLeft))
			delete cols[i].paddingLeft;
		if(!isValidSize(cols[i].paddingRight))
			delete cols[i].paddingRight;
	}

	scheduler[objName].select = obj.select === undefined ? true : obj.select;
	if(scheduler.locale.labels[name +'_tab'] === undefined)
		scheduler.locale.labels[name +'_tab'] = scheduler[objName].label || scheduler.locale.labels.grid_tab;

	scheduler[objName]._selected_divs = [];

	scheduler.date[name+'_start']=function(d){ return d; };
	scheduler.date['add_' + name] = function(date, inc){
		var ndate = new Date(date);
		ndate.setMonth(ndate.getMonth()+inc);
		return ndate;
	};

	scheduler.templates[name+"_date"] = function(start, end){
		return scheduler.templates.day_date(start)+" - "+scheduler.templates.day_date(end)
	}

	scheduler.attachEvent("onTemplatesReady",function(){

		scheduler.templates[name + '_full_date'] = function(start,end,ev){
			if (ev._timed)
				return this.day_date(ev.start_date, ev.end_date, ev)+" "+this.event_date(start);
			else
				return scheduler.templates.day_date(start)+" &ndash; "+scheduler.templates.day_date(end);
		};
		scheduler.templates[name + '_single_date'] = function(date){
			return scheduler.templates.day_date(date)+" "+this.event_date(date);
		}


		scheduler.attachEvent("onDblClick",function(event_id, native_event_object){
			if(this._mode == name){
				scheduler._click.buttons['details'](event_id)
				return false;
			}
			return true;
		});

		scheduler.attachEvent("onClick",function(event_id, native_event_object){
			if(this._mode == name && scheduler[objName].select ){
				scheduler.grid.unselectEvent('', name);
				scheduler.grid.selectEvent(event_id, name, native_event_object);
				return false;
			}
			return true;
		});


		scheduler.templates[name + '_field'] = function(field_name, event){
			return event[field_name];
		};

		scheduler.attachEvent("onSchedulerResize", function() {
			if (this._mode == name) {
				this[name + '_view'](true);
				// timeout used to run code after all onSchedulerResize handlers are finished
				window.setTimeout(function(){
					// we need to call event manually because handler return false, and blocks default logic
					scheduler.callEvent("onAfterSchedulerResize", []);
				},1);
				return false;
			}
			return true;
		});


		var old = scheduler.render_data;
		scheduler.render_data=function(evs){
			if (this._mode == name)
				scheduler.grid._fill_grid_tab(objName);
			else
				return old.apply(this,arguments);
		};

		var old_render_view_data = scheduler.render_view_data;
		scheduler.render_view_data=function(){
			if(this._mode == name) {
				scheduler.grid._gridScrollTop = scheduler._els["dhx_cal_data"][0].childNodes[0].scrollTop;
				scheduler._els["dhx_cal_data"][0].childNodes[0].scrollTop = 0;
				scheduler._els["dhx_cal_data"][0].style.overflowY = 'auto';
			}
			else {
				scheduler._els["dhx_cal_data"][0].style.overflowY = 'auto';
			}
			return old_render_view_data.apply(this,arguments);
		}
});


	scheduler[name+'_view']=function(mode){
		if (mode){
			scheduler._min_date = scheduler[objName].paging ? scheduler.date[name+'_start'](new Date(scheduler._date)) : scheduler.config[name + '_start'];
			scheduler._max_date = scheduler[objName].paging ? scheduler.date.add(scheduler._min_date, 1, name) : scheduler.config[name + '_end'];

			scheduler.grid.set_full_view(objName);
			if(scheduler._min_date > new Date(0) && scheduler._max_date < (new Date(9999,1,1)))
				scheduler._els["dhx_cal_date"][0].innerHTML=scheduler.templates[name+"_date"](scheduler._min_date,scheduler._max_date);
			else
				scheduler._els["dhx_cal_date"][0].innerHTML="";

			//grid tab activated
			scheduler.grid._fill_grid_tab(objName);
			scheduler._gridView = objName;
		} else {
			scheduler.grid._sort_marker = null;
			delete scheduler._gridView;
			scheduler._rendered=[];
			scheduler[objName]._selected_divs = [];
			//grid tab de-activated
		}
	};


}


scheduler.dblclick_dhx_grid_area=function(){
	if (!this.config.readonly && this.config.dblclick_create)
		this.addEventNow();
};

if(scheduler._click.dhx_cal_header){
 	scheduler._old_header_click = scheduler._click.dhx_cal_header;
}
scheduler._click.dhx_cal_header=function(e){
	if(scheduler._gridView){
		var event = e||window.event;
		var params = scheduler.grid.get_sort_params(event, scheduler._gridView);

		scheduler.grid.draw_sort_marker(event.originalTarget || event.srcElement, params.dir);

		scheduler.clear_view();
		scheduler.grid._fill_grid_tab(scheduler._gridView, params);
	}
	else if(scheduler._old_header_click)
		return scheduler._old_header_click.apply(this,arguments);
};

scheduler.grid.selectEvent = function(id, view_name, native_event_object){
	if(scheduler.callEvent("onBeforeRowSelect",[id,native_event_object])){
		var objName = scheduler.grid._getObjName(view_name);

		scheduler.for_rendered(id, function(event_div){
			event_div.className += " dhx_grid_event_selected";
			scheduler[objName]._selected_divs.push(event_div);
		});
		scheduler._select_id = id;
	}
};

scheduler.grid._unselectDiv= function(div){
	div.className = div.className.replace(/ dhx_grid_event_selected/,'');
}
scheduler.grid.unselectEvent = function(id, view_name){
	var objName = scheduler.grid._getObjName(view_name);
	if(!objName || !scheduler[objName]._selected_divs)
		return;

	if(!id){
		for(var i=0; i<scheduler[objName]._selected_divs.length; i++)
			scheduler.grid._unselectDiv(scheduler[objName]._selected_divs[i]);

		scheduler[objName]._selected_divs = [];

	}else{
		for(var i=0; i<scheduler[objName]._selected_divs.length; i++)
			if(scheduler[objName]._selected_divs[i].getAttribute('event_id') == id){
				scheduler.grid._unselectDiv(scheduler[objName]._selected_divs[i]);
				scheduler[objName]._selected_divs.slice(i,1);
				break;
			}

	}
};

scheduler.grid.get_sort_params = function(event, objName){
	var targ = event.originalTarget || event.srcElement;
	if(targ.className == 'dhx_grid_view_sort')
		targ = targ.parentNode;
	if(!targ.className || targ.className.indexOf("dhx_grid_sort_asc") == -1)
		var direction = 'asc';
	else
		var direction = 'desc';

	var index = 0;
	for(var i =0; i < targ.parentNode.childNodes.length; i++){
		if(targ.parentNode.childNodes[i] == targ){
			index = i;
			break;
		}
	}



	var value = null;
	if(scheduler[objName].columns[index].template){
		var template = scheduler[objName].columns[index].template
		value = function(ev){
			return template(ev.start_date, ev.end_date, ev);
		};
	}else{
		var field = scheduler[objName].columns[index].id;
		if(field == "date")
			field = "start_date";
		value = function(ev){ return ev[field];}
	}

	var rule = scheduler[objName].columns[index].sort;

	if(typeof rule != 'function'){
		rule = scheduler.grid.sort_rules[rule] || scheduler.grid.sort_rules['str'];
	}

	return {dir:direction, value:value, rule:rule};
};

scheduler.grid.draw_sort_marker = function(node, direction){
	if(node.className == 'dhx_grid_view_sort')
		node = node.parentNode;

	if(scheduler.grid._sort_marker){
		scheduler.grid._sort_marker.className = scheduler.grid._sort_marker.className.replace(/( )?dhx_grid_sort_(asc|desc)/, '');
		scheduler.grid._sort_marker.removeChild(scheduler.grid._sort_marker.lastChild);
	}

	node.className += " dhx_grid_sort_"+direction;
	scheduler.grid._sort_marker = node;
	var html = "<div class='dhx_grid_view_sort' style='left:"+(+node.style.width.replace('px','') -15+node.offsetLeft)+"px'>&nbsp;</div>";
	node.innerHTML += html;

};

scheduler.grid.sort_grid=function(sort){

	var sort = sort || {dir:'desc', value:function(ev){return ev.start_date;}, rule:scheduler.grid.sort_rules['date']};

	var events = scheduler.get_visible_events();

	if(sort.dir == 'desc')
		events.sort(function(a,b){return sort.rule(a,b,sort.value)});
	else
		events.sort(function(a,b){return -sort.rule(a,b, sort.value)});
	return events;
};



scheduler.grid.set_full_view = function(mode){
	if (mode){
		var l = scheduler.locale.labels;
		var html =scheduler.grid._print_grid_header(mode);

		scheduler._els["dhx_cal_header"][0].innerHTML= html;
		scheduler._table_view=true;
		scheduler.set_sizes();
	}
};
scheduler.grid._calcPadding = function(column, parent){
	var padding = (column.paddingLeft !== undefined ? 1*column.paddingLeft : scheduler[parent].defPadding)
				+ (column.paddingRight !== undefined ? 1*column.paddingRight : scheduler[parent].defPadding);
	return padding;
};

scheduler.grid._getStyles = function(column, items){
	var cell_style = [], style = "";
	for(var i=0; items[i]; i++ ){
		style = items[i] + ":";
	    switch (items[i]){
			case "text-align":
				if(column.align)
					cell_style.push(style+column.align);
				break;
			case "vertical-align":
				if(column.valign)
					cell_style.push(style+column.valign);
				break;
			case "padding-left":
				if(column.paddingLeft != undefined)
					cell_style.push(style+(column.paddingLeft||'0') + "px");
				break;
			case "padding-left":
				if(column.paddingRight != undefined)
					cell_style.push(style+(column.paddingRight||'0') + "px");
				break;
		}
	}
	return cell_style;
};

scheduler.grid._fill_grid_tab = function(objName, sort){
	//get current date
	var date = scheduler._date;
	//select events for which data need to be printed
	var events = scheduler.grid.sort_grid(sort)

	//generate html for the view
	var columns = scheduler[objName].columns;

	var html = "<div>";
	var left = -2;//column borders at the same pos as header borders...
	for(var i=0; i < columns.length; i++){
		var padding = scheduler.grid._calcPadding(columns[i], objName);
		left +=columns[i].width + padding ;//
		if(i < columns.length - 1)
			html += "<div class='dhx_grid_v_border' style='left:"+(left)+"px'></div>";
	}
	html += "</div>"
	html +="<div class='dhx_grid_area'><table>";

	for (var i=0; i<events.length; i++){
		html += scheduler.grid._print_event_row(events[i], objName);
	}

	html +="</table></div>";
	//render html
	scheduler._els["dhx_cal_data"][0].innerHTML = html;
	scheduler._els["dhx_cal_data"][0].scrollTop = scheduler.grid._gridScrollTop||0;

	var t=scheduler._els["dhx_cal_data"][0].getElementsByTagName("tr");

	scheduler._rendered=[];
	for (var i=0; i < t.length; i++){
		scheduler._rendered[i]=t[i]
	}

};
scheduler.grid._print_event_row = function(ev, objName){

	var styles = [];
	if(ev.color)
		styles.push("background:"+ev.color);
	if(ev.textColor)
		styles.push("color:"+ev.textColor);
	if(ev._text_style)
		styles.push(ev._text_style);
	if(scheduler[objName]['rowHeight'])
			styles.push('height:'+scheduler[objName]['rowHeight'] + 'px');

	var style = "";
	if(styles.length){
		style = "style='"+styles.join(";")+"'";
	}

	var columns = scheduler[objName].columns;
	var ev_class = scheduler.templates.event_class(ev.start_date, ev.end_date, ev);

	var html ="<tr class='dhx_grid_event"+(ev_class? ' '+ev_class:'')+"' event_id='"+ev.id+"' " + style + ">";

	var name = scheduler.grid._getViewName(objName);
	var availStyles = ["text-align", "vertical-align", "padding-left","padding-right"];
	for(var i =0; i < columns.length; i++){
		var value;
		if(columns[i].template){
			value = columns[i].template(ev.start_date, ev.end_date, ev);
		}else if(columns[i].id == 'date') {
			value = scheduler.templates[name + '_full_date'](ev.start_date, ev.end_date, ev);
		}else if(columns[i].id == 'start_date' || columns[i].id == 'end_date' ){
	        value = scheduler.templates[name + '_single_date'](ev[columns[i].id]);
		}else{
			value = scheduler.templates[name + '_field'](columns[i].id, ev);
		}

		var cell_style = scheduler.grid._getStyles(columns[i], availStyles);

		var className = columns[i].css ? (" class=\""+columns[i].css+"\"") : "";

		html+= "<td style='width:"+ (columns[i].width )+"px;"+cell_style.join(";")+"' "+className+">"+value+"</td>";

	}
	html+="<td class='dhx_grid_dummy'></td></tr>";

	return html;
};

scheduler.grid._print_grid_header = function(objName){
	var head = "<div class='dhx_grid_line'>";

	var columns = scheduler[objName].columns;
	var widths = [];

	var unsized_columns = columns.length;
	var avail_width = scheduler._obj.clientWidth - 2*columns.length -20;//-20 for possible scrollbar, -length for borders
	for(var ind=0; ind < columns.length; ind++){

		var val = columns[ind].initialWidth*1;
		if(!isNaN(val) && columns[ind].initialWidth != '' && columns[ind].initialWidth != null && typeof columns[ind].initialWidth != 'boolean'){

			unsized_columns--;
			avail_width -= val;
			widths[ind] = val;
		}else {
			widths[ind] = null;
		}
	}

	var unsized_width = Math.floor(avail_width / unsized_columns);
	var availStyles = ["text-align",  "padding-left","padding-right"];
	for(var i=0; i < columns.length; i++){
		var column_width = !widths[i] ? unsized_width : widths[i];
		columns[i].width = column_width - scheduler.grid._calcPadding(columns[i], objName);
		var cell_style = scheduler.grid._getStyles(columns[i], availStyles);
		head += "<div style='width:"+(columns[i].width -1)+"px;"+cell_style.join(";")+"'>" + (columns[i].label === undefined ? columns[i].id : columns[i].label) + "</div>";
	}
	head +="</div>";

	return head;
};
