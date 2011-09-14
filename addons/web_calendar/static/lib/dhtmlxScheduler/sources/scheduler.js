/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
window.dhtmlXScheduler=window.scheduler={version:3.0};
dhtmlxEventable(scheduler);
scheduler.init=function(id,date,mode){
	date=date||(new Date());
	mode=mode||"week";

	scheduler.date.init();
	
	this._obj=(typeof id == "string")?document.getElementById(id):id;
	this._els=[];
	this._scroll=true;
	this._quirks=(_isIE && document.compatMode == "BackCompat");
	this._quirks7=(_isIE && navigator.appVersion.indexOf("MSIE 8")==-1);
	
	this.get_elements();
	this.init_templates();
	this.set_actions();
	dhtmlxEvent(window,"resize",function(){
		window.clearTimeout(scheduler._resize_timer);
		scheduler._resize_timer=window.setTimeout(function(){
			if (scheduler.callEvent("onSchedulerResize",[]))
				scheduler.update_view();
		}, 100);
	});
	this.set_sizes();
	scheduler.callEvent('onSchedulerReady', []);
	this.setCurrentView(date,mode);
};
scheduler.xy={
	nav_height:22,
	min_event_height:40,
	scale_width:50,
	bar_height:20,
	scroll_width:18,
	scale_height:20,
	month_scale_height:20,
	menu_width:25,
	margin_top:0,
	margin_left:0,
	editor_width:140
};
scheduler.keys={
	edit_save:13,
	edit_cancel:27
};
scheduler.set_sizes=function(){
	var w = this._x = this._obj.clientWidth-this.xy.margin_left;
	var h = this._y = this._obj.clientHeight-this.xy.margin_top;
	
	//not-table mode always has scroll - need to be fixed in future
	var scale_x=this._table_view?0:(this.xy.scale_width+this.xy.scroll_width);
	var scale_s=this._table_view?-1:this.xy.scale_width;
	
	this.set_xy(this._els["dhx_cal_navline"][0],w,this.xy.nav_height,0,0);
	this.set_xy(this._els["dhx_cal_header"][0],w-scale_x,this.xy.scale_height,scale_s,this.xy.nav_height+(this._quirks?-1:1));
	//to support alter-skin, we need a way to alter height directly from css
	var actual_height = this._els["dhx_cal_navline"][0].offsetHeight;
	if (actual_height > 0) this.xy.nav_height = actual_height;
	
	var data_y=this.xy.scale_height+this.xy.nav_height+(this._quirks?-2:0);
	this.set_xy(this._els["dhx_cal_data"][0],w,h-(data_y+2),0,data_y+2);
};
scheduler.set_xy=function(node,w,h,x,y){
	node.style.width=Math.max(0,w)+"px";
	node.style.height=Math.max(0,h)+"px";
	if (arguments.length>3){
		node.style.left=x+"px";
		node.style.top=y+"px";	
	}
};
scheduler.get_elements=function(){
	//get all child elements as named hash
	var els=this._obj.getElementsByTagName("DIV");
	for (var i=0; i < els.length; i++){
		var name=els[i].className;
		if (!this._els[name]) this._els[name]=[];
		this._els[name].push(els[i]);
		
		//check if name need to be changed
		var t=scheduler.locale.labels[els[i].getAttribute("name")||name];
		if (t) els[i].innerHTML=t;
	}
};
scheduler.set_actions=function(){
	for (var a in this._els)
		if (this._click[a])
			for (var i=0; i < this._els[a].length; i++)
				this._els[a][i].onclick=scheduler._click[a];
	this._obj.onselectstart=function(e){ return false; };
	this._obj.onmousemove=function(e){
		scheduler._on_mouse_move(e||event);
	};
	this._obj.onmousedown=function(e){
		scheduler._on_mouse_down(e||event);
	};
	this._obj.onmouseup=function(e){
		scheduler._on_mouse_up(e||event);
	};
	this._obj.ondblclick=function(e){
		scheduler._on_dbl_click(e||event);
	}
};
scheduler.select=function(id){
	if (this._table_view || !this.getEvent(id)._timed) return; //temporary block
	if (this._select_id==id) return;
	this.editStop(false);
	this.unselect();
	this._select_id = id;
	this.updateEvent(id);
};
scheduler.unselect=function(id){
	if (id && id!=this._select_id) return;
	var t=this._select_id;
	this._select_id = null;
	if (t) this.updateEvent(t);
};
scheduler.getState=function(){
	return {
		mode: this._mode,
		date: this._date,
		min_date: this._min_date,
		max_date: this._max_date,
		editor_id: this._edit_id,
		lightbox_id: this._lightbox_id,
        new_event: this._new_event
	};
};
scheduler._click={
	dhx_cal_data:function(e){
        //debugger;
		var trg = e?e.target:event.srcElement;
		var id = scheduler._locate_event(trg);
		
		e = e || event;
		if ((id && !scheduler.callEvent("onClick",[id,e])) ||scheduler.config.readonly) return;
		
		if (id) {		
			scheduler.select(id);
			var mask = trg.className;
			if (mask.indexOf("_icon")!=-1)
				scheduler._click.buttons[mask.split(" ")[1].replace("icon_","")](id);
		} else
			scheduler._close_not_saved();
	},
	dhx_cal_prev_button:function(){
		scheduler._click.dhx_cal_next_button(0,-1);
	},
	dhx_cal_next_button:function(dummy,step){
		scheduler.setCurrentView(scheduler.date.add( //next line changes scheduler._date , but seems it has not side-effects
			scheduler.date[scheduler._mode+"_start"](scheduler._date),(step||1),scheduler._mode));
	},
	dhx_cal_today_button:function(){
		scheduler.setCurrentView(new Date());
	},
	dhx_cal_tab:function(){
		var name = this.getAttribute("name");
		var mode = name.substring(0, name.search("_tab"));
		scheduler.setCurrentView(scheduler._date,mode);
	},
	buttons:{
		"delete":function(id){ var c=scheduler.locale.labels.confirm_deleting; if (!c||confirm(c)) scheduler.deleteEvent(id); },
		edit:function(id){ scheduler.edit(id); },
		save:function(id){ scheduler.editStop(true); },
		details:function(id){ scheduler.showLightbox(id); },
		cancel:function(id){ scheduler.editStop(false); }
	}
};
scheduler.addEventNow=function(start,end,e){
	var base = {};
	if (start && start.constructor.toString().match(/object/i) !== null){
		base = start;
		start = null;
	}
	
	var d = (this.config.event_duration||this.config.time_step)*60000;
	if (!start) start = Math.round((new Date()).valueOf()/d)*d;
	var start_date = new Date(start);
	if (!end){
		var start_hour = this.config.first_hour;
		if (start_hour > start_date.getHours()){
			start_date.setHours(start_hour);
			start = start_date.valueOf();
		}
		end = start+d;
	}
	var end_date = new Date(end);

	// scheduler.addEventNow(new Date(), new Date()) + collision though get_visible events defect (such event was not retrieved)
	if(start_date.valueOf() == end_date.valueOf())
		end_date.setTime(end_date.valueOf()+d);

	base.start_date = base.start_date||start_date;
	base.end_date =  base.end_date||end_date;
	base.text = base.text||this.locale.labels.new_event;
	base.id = this._drag_id = this.uid();
	this._drag_mode="new-size";

	this._loading=true;
	this.addEvent(base);
	this.callEvent("onEventCreated",[this._drag_id,e]);
	this._loading=false;
	
	this._drag_event={}; //dummy , to trigger correct event updating logic
	this._on_mouse_up(e);	
};
scheduler._on_dbl_click=function(e,src){
	src = src||(e.target||e.srcElement);
	if (this.config.readonly) return;
	var name = src.className.split(" ")[0];
	switch(name){
		case "dhx_scale_holder":
		case "dhx_scale_holder_now":
		case "dhx_month_body":
		case "dhx_wa_day_data":
			if (!scheduler.config.dblclick_create) break;
			var pos=this._mouse_coords(e);
			var start=this._min_date.valueOf()+(pos.y*this.config.time_step+(this._table_view?0:pos.x)*24*60)*60000;
			start = this._correct_shift(start);
			this.addEventNow(start,null,e);
			break;
		case "dhx_body":
		case "dhx_wa_ev_body":
		case "dhx_cal_event_line":
		case "dhx_cal_event_clear":
			var id = this._locate_event(src);
			if (!this.callEvent("onDblClick",[id,e])) return;
			if (this.config.details_on_dblclick || this._table_view || !this.getEvent(id)._timed)
				this.showLightbox(id);
			else
				this.edit(id);
			break;
		case "":
			if (src.parentNode)
				return scheduler._on_dbl_click(e,src.parentNode);			
		default:
			var t = this["dblclick_"+name];
			if (t) t.call(this,e);
			break;
	}
};

scheduler._mouse_coords=function(ev){
	var pos;
	var b=document.body;
	var d = document.documentElement;
	if(ev.pageX || ev.pageY)
	    pos={x:ev.pageX, y:ev.pageY};
	else pos={
	    x:ev.clientX + (b.scrollLeft||d.scrollLeft||0) - b.clientLeft,
	    y:ev.clientY + (b.scrollTop||d.scrollTop||0) - b.clientTop
	};

	//apply layout
	pos.x-=getAbsoluteLeft(this._obj)+(this._table_view?0:this.xy.scale_width);
	pos.y-=getAbsoluteTop(this._obj)+this.xy.nav_height+(this._dy_shift||0)+this.xy.scale_height-this._els["dhx_cal_data"][0].scrollTop;
	pos.ev = ev;

	var handler = this["mouse_"+this._mode];
	if (handler)
		return handler.call(this,pos);

	//transform to date
	if (!this._table_view){
		pos.x=Math.max(0,Math.ceil(pos.x/this._cols[0])-1);
		pos.y=Math.max(0,Math.ceil(pos.y*60/(this.config.time_step*this.config.hour_size_px))-1)+this.config.first_hour*(60/this.config.time_step);
	} else {
		var dy=0;
		for (dy=1; dy < this._colsS.heights.length; dy++)
			if (this._colsS.heights[dy]>pos.y) break;

		pos.y=(Math.max(0,Math.ceil(pos.x/this._cols[0])-1)+Math.max(0,dy-1)*7)*24*60/this.config.time_step;
		pos.x=0;
	}

	return pos;
}
scheduler._close_not_saved=function(){
	if (new Date().valueOf()-(scheduler._new_event||0) > 500 && scheduler._edit_id){
		var c=scheduler.locale.labels.confirm_closing;
		if (!c || confirm(c))
			scheduler.editStop(scheduler.config.positive_closing);
	}
};
scheduler._correct_shift=function(start, back){
	return start-=((new Date(scheduler._min_date)).getTimezoneOffset()-(new Date(start)).getTimezoneOffset())*60000*(back?-1:1);	
};
scheduler._on_mouse_move=function(e){
	if (this._drag_mode){
		var pos=this._mouse_coords(e);
		if (!this._drag_pos || pos.custom || this._drag_pos.x!=pos.x || this._drag_pos.y!=pos.y){
			
			if (this._edit_id!=this._drag_id)
				this._close_not_saved();
				
			this._drag_pos=pos;
			
			if (this._drag_mode=="create"){
				this._close_not_saved();
				this._loading=true; //will be ignored by dataprocessor
				
				var start=this._min_date.valueOf()+(pos.y*this.config.time_step+(this._table_view?0:pos.x)*24*60)*60000;
				//if (this._mode != "week" && this._mode != "day")
				start = this._correct_shift(start);
				
				if (!this._drag_start){
					this._drag_start=start; return; 
				}
				var end = start;
				if (end==this._drag_start) return;
				
				this._drag_id=this.uid();
				this.addEvent(new Date(this._drag_start), new Date(end),this.locale.labels.new_event,this._drag_id, pos.fields);
				
				this.callEvent("onEventCreated",[this._drag_id,e]);
				this._loading=false;
				this._drag_mode="new-size";
				
			} 

			var ev=this.getEvent(this._drag_id);
			var start,end;
			if (this._drag_mode=="move"){
				start = this._min_date.valueOf()+(pos.y*this.config.time_step+pos.x*24*60)*60000;
				if (!pos.custom && this._table_view) start+=this.date.time_part(ev.start_date)*1000;
				start = this._correct_shift(start);
				end = ev.end_date.valueOf()-(ev.start_date.valueOf()-start);
			} else {
				start = ev.start_date.valueOf();
				if (this._table_view) {
					end = this._min_date.valueOf()+pos.y*this.config.time_step*60000 + (pos.custom?0:24*60*60000);
					if (this._mode == "month")
						end = this._correct_shift(end, false);
				}
				else{
					end = this.date.date_part(new Date(ev.end_date)).valueOf()+pos.y*this.config.time_step*60000;
					this._els["dhx_cal_data"][0].style.cursor="s-resize";
					if (this._mode == "week" || this._mode == "day")
						end = this._correct_shift(end);
				}
				if (this._drag_mode == "new-size"){ 
					if (end <= this._drag_start){
						var shift = pos.shift||((this._table_view && !pos.custom)?24*60*60000:0);
						start = end-(pos.shift?0:shift);
						end = this._drag_start+(shift||(this.config.time_step*60000));
					} else {
						start = this._drag_start;
					}
					
				} else if (end<=start) 
					end=start+this.config.time_step*60000;
			}
			var new_end = new Date(end-1);			
			var new_start = new Date(start);
			//prevent out-of-borders situation for day|week view
			if ( this._table_view || (new_end.getDate()==new_start.getDate() && new_end.getHours()<this.config.last_hour) || (scheduler._wa && scheduler._wa._dnd) ){
				ev.start_date=new_start;
				ev.end_date=new Date(end);
				if (this.config.update_render)
					this.update_view();
				else
					this.updateEvent(this._drag_id);
			}
			if (this._table_view)
				this.for_rendered(this._drag_id,function(r){
					r.className+=" dhx_in_move";
				})
		}
	}  else {
		if (scheduler.checkEvent("onMouseMove")){
			
			var id = this._locate_event(e.target||e.srcElement);
			this.callEvent("onMouseMove",[id,e]);
		}
	}
};
scheduler._on_mouse_context=function(e,src){
	return this.callEvent("onContextMenu",[this._locate_event(src),e]);
};
scheduler._on_mouse_down=function(e,src){
	if (this.config.readonly || this._drag_mode) return;
	src = src||(e.target||e.srcElement);
	if (e.button==2||e.ctrlKey) return this._on_mouse_context(e,src);
		switch(src.className.split(" ")[0]){
		case "dhx_cal_event_line":
		case "dhx_cal_event_clear":
			if (this._table_view)
				this._drag_mode="move"; //item in table mode
			break;
		case "dhx_header":
		case "dhx_title":
		case "dhx_wa_ev_body":
			this._drag_mode="move"; //item in table mode
			break;
		case "dhx_footer":
			this._drag_mode="resize"; //item in table mode
			break;
		case "dhx_scale_holder":
		case "dhx_scale_holder_now":
		case "dhx_month_body":
		case "dhx_matrix_cell":
			this._drag_mode="create";
			break;
		case "":
			if (src.parentNode)
				return scheduler._on_mouse_down(e,src.parentNode);
		default:
			this._drag_mode=null;
			this._drag_id=null;
	}
	if (this._drag_mode){
		var id = this._locate_event(src);
		if (!this.config["drag_"+this._drag_mode] || !this.callEvent("onBeforeDrag",[id, this._drag_mode, e]))
			this._drag_mode=this._drag_id=0;
		else {
			this._drag_id= id;
            this._drag_event=scheduler._lame_copy({},this._copy_event(this.getEvent(this._drag_id)||{}));
		}
	}
	this._drag_start=null;
};
scheduler._on_mouse_up=function(e){
	if (this._drag_mode && this._drag_id){
		this._els["dhx_cal_data"][0].style.cursor="default";
		//drop
		var ev=this.getEvent(this._drag_id);
		if (this._drag_event._dhx_changed || !this._drag_event.start_date || ev.start_date.valueOf()!=this._drag_event.start_date.valueOf() || ev.end_date.valueOf()!=this._drag_event.end_date.valueOf()){
			var is_new=(this._drag_mode=="new-size");
			if (!this.callEvent("onBeforeEventChanged",[ev,e,is_new])){
				if (is_new) 
					this.deleteEvent(ev.id, true);
				else {
                    this._drag_event._dhx_changed = false;
                    scheduler._lame_copy(ev, this._drag_event);
					this.updateEvent(ev.id);
				}
			} else {
				if (is_new && this.config.edit_on_create){
					this.unselect();
					this._new_event=new Date();//timestamp of creation
					if (this._table_view || this.config.details_on_create) {
						this._drag_mode=null;
						return this.showLightbox(this._drag_id);
					}
					this._drag_pos=true; //set flag to trigger full redraw
					this._select_id=this._edit_id=this._drag_id;
				} else if (!this._new_event)
					this.callEvent(is_new?"onEventAdded":"onEventChanged",[this._drag_id,this.getEvent(this._drag_id)]);
			}
		}
		if (this._drag_pos) this.render_view_data(); //redraw even if there is no real changes - necessary for correct positioning item after drag
	}
	this._drag_mode=null;
	this._drag_pos=null;
};
scheduler.update_view=function(){
	this._reset_scale();
	if (this._load_mode && this._load()) return this._render_wait = true;
	this.render_view_data();
};
scheduler.setCurrentView=function(date,mode){
	date = date || this._date;
    mode = mode || this._mode;
	
	if (!this.callEvent("onBeforeViewChange",[this._mode,this._date,mode,date])) return;

    var dhx_cal_data = 'dhx_cal_data';
    var prev_scroll = (this._mode == mode && this.config.preserve_scroll)?this._els[dhx_cal_data][0].scrollTop:false; // saving current scroll

	//hide old custom view
	if (this[this._mode+"_view"] && mode && this._mode!=mode)
		this[this._mode+"_view"](false);
		
	this._close_not_saved();

    var dhx_multi_day = 'dhx_multi_day';
	if(this._els[dhx_multi_day]) {
		this._els[dhx_multi_day][0].parentNode.removeChild(this._els[dhx_multi_day][0]);
		this._els[dhx_multi_day] = null;
	}
	
	this._mode=mode;
	this._date=date;
	this._table_view=(this._mode=="month");
	
	var tabs=this._els["dhx_cal_tab"];
	for (var i=0; i < tabs.length; i++) {
		tabs[i].className="dhx_cal_tab"+((tabs[i].getAttribute("name")==this._mode+"_tab")?" active":"");
	}
	
	//show new view
	var view=this[this._mode+"_view"];
	view?view(true):this.update_view();

    if(typeof prev_scroll == "number") // if we are updating or working with the same view scrollTop should be saved
        this._els[dhx_cal_data][0].scrollTop = prev_scroll; // restoring original scroll
	
	this.callEvent("onViewChange",[this._mode,this._date]);
};
scheduler._render_x_header = function(i,left,d,h){
	//header scale	
	var head=document.createElement("DIV"); head.className="dhx_scale_bar";
	this.set_xy(head,this._cols[i]-1,this.xy.scale_height-2,left,0);//-1 for border
	head.innerHTML=this.templates[this._mode+"_scale_date"](d,this._mode); //TODO - move in separate method
	h.appendChild(head);
};
scheduler._reset_scale=function(){
	//current mode doesn't support scales
	//we mustn't call reset_scale for such modes, so it just to be sure
	if (!this.templates[this._mode+"_date"]) return;
	
	var h=this._els["dhx_cal_header"][0];
	var b=this._els["dhx_cal_data"][0];
	var c = this.config;
	
	h.innerHTML="";
	b.scrollTop=0; //fix flickering in FF
	b.innerHTML="";
	
	
	var str=((c.readonly||(!c.drag_resize))?" dhx_resize_denied":"")+((c.readonly||(!c.drag_move))?" dhx_move_denied":"");
	if (str) b.className = "dhx_cal_data"+str;
		
		
	this._cols=[];	//store for data section
	this._colsS={height:0};
	this._dy_shift=0;
	
	this.set_sizes();
	var summ=parseInt(h.style.width); //border delta
	var left=0;
	
	var d,dd,sd,today;
	dd=this.date[this._mode+"_start"](new Date(this._date.valueOf()));
	d=sd=this._table_view?scheduler.date.week_start(dd):dd;
	today=this.date.date_part(new Date());
	
	//reset date in header
	var ed=scheduler.date.add(dd,1,this._mode);
	var count = 7;
	
	if (!this._table_view){
		var count_n = this.date["get_"+this._mode+"_end"];
		if (count_n) ed = count_n(dd);
		count = Math.round((ed.valueOf()-dd.valueOf())/(1000*60*60*24));
	}
	
	this._min_date=d;
	this._els["dhx_cal_date"][0].innerHTML=this.templates[this._mode+"_date"](dd,ed,this._mode);
	
	for (var i=0; i<count; i++){ 
		this._cols[i]=Math.floor(summ/(count-i));
	
		this._render_x_header(i,left,d,h);
		if (!this._table_view){
			var scales=document.createElement("DIV");
			var cls = "dhx_scale_holder"
			if (d.valueOf()==today.valueOf()) cls = "dhx_scale_holder_now";
			scales.className=cls+" "+this.templates.week_date_class(d,today);
			this.set_xy(scales,this._cols[i]-1,c.hour_size_px*(c.last_hour-c.first_hour),left+this.xy.scale_width+1,0);//-1 for border
			b.appendChild(scales);
			this.callEvent("onScaleAdd",[scales, d]);
		}
		
		d=this.date.add(d,1,"day");
		summ-=this._cols[i];
		left+=this._cols[i];
		this._colsS[i]=(this._cols[i-1]||0)+(this._colsS[i-1]||(this._table_view?0:this.xy.scale_width+2));
		this._colsS['col_length'] = count+1;
	}
	this._max_date=d;
	this._colsS[count]=this._cols[count-1]+this._colsS[count-1];
	
	if (this._table_view) // month view
		this._reset_month_scale(b,dd,sd);
	else{
		this._reset_hours_scale(b,dd,sd);
		if (c.multi_day){
            var dhx_multi_day = 'dhx_multi_day';

			if(this._els[dhx_multi_day]) {
				this._els[dhx_multi_day][0].parentNode.removeChild(this._els[dhx_multi_day][0]);
				this._els[dhx_multi_day] = null;
			}
			
			var navline = this._els["dhx_cal_navline"][0];
			var top = navline.offsetHeight + this._els["dhx_cal_header"][0].offsetHeight+1;
			
			var c1 = document.createElement("DIV");
			c1.className = dhx_multi_day;
			c1.style.visibility="hidden";
			this.set_xy(c1, this._colsS[this._colsS.col_length-1]+this.xy.scroll_width, 0, 0, top); // 2 extra borders, dhx_header has -1 bottom margin
			b.parentNode.insertBefore(c1,b);
			
			var c2 = c1.cloneNode(true);
			c2.className = dhx_multi_day+"_icon";
			c2.style.visibility="hidden";
			this.set_xy(c2, this.xy.scale_width, 0, 0, top); // dhx_header has -1 bottom margin
			
			c1.appendChild(c2);
			this._els[dhx_multi_day]=[c1,c2];
            this._els[dhx_multi_day][0].onclick = this._click.dhx_cal_data;
		}
		
		if (this.config.mark_now){
			var now = new Date();
			if (now < this._max_date && now > this._min_date && now.getHours() >= this.config.first_hour && now.getHours()<this.config.last_hour){
				var day = this.locate_holder_day(now);
				var sm = now.getHours()*60+now.getMinutes();
				var now_time = document.createElement("DIV");
				now_time.className = "dhx_now_time";
				now_time.style.top = (Math.round((sm*60*1000-this.config.first_hour*60*60*1000)*this.config.hour_size_px/(60*60*1000)))%(this.config.hour_size_px*24)+1+"px"; 
				b.childNodes[day].appendChild(now_time);
			}
		}			
	}
};
scheduler._reset_hours_scale=function(b,dd,sd){
	var c=document.createElement("DIV");
	c.className="dhx_scale_holder";
	
	var date = new Date(1980,1,1,this.config.first_hour,0,0);
	for (var i=this.config.first_hour*1; i < this.config.last_hour; i++) {
		var cc=document.createElement("DIV");
		cc.className="dhx_scale_hour";
		cc.style.height=this.config.hour_size_px-(this._quirks?0:1)+"px";
		cc.style.width=this.xy.scale_width+"px";
		cc.innerHTML=scheduler.templates.hour_scale(date);
		
		c.appendChild(cc);
		date=this.date.add(date,1,"hour");
	};
	b.appendChild(c);
	if (this.config.scroll_hour)
		b.scrollTop = this.config.hour_size_px*(this.config.scroll_hour-this.config.first_hour);
};
scheduler._reset_month_scale=function(b,dd,sd){
	var ed=scheduler.date.add(dd,1,"month");
	
	//trim time part for comparation reasons
	var cd=new Date();
	this.date.date_part(cd);
	this.date.date_part(sd);

	var rows=Math.ceil(Math.round((ed.valueOf()-sd.valueOf()) / (60*60*24*1000) ) / 7);
	var tdcss=[];
	var height=(Math.floor(b.clientHeight/rows)-22);
	
	this._colsS.height=height+22;
	var h = this._colsS.heights = [];
	for (var i=0; i<=7; i++)
		tdcss[i]=" style='height:"+height+"px; width:"+((this._cols[i]||0)-1)+"px;' "

	
	
	var cellheight = 0;
	this._min_date=sd;
	var html="<table cellpadding='0' cellspacing='0'>";
	for (var i=0; i<rows; i++){
		html+="<tr>";
			for (var j=0; j<7; j++){
				html+="<td";
				var cls = "";
				if (sd<dd)
					cls='dhx_before';
				else if (sd>=ed)
					cls='dhx_after';
				else if (sd.valueOf()==cd.valueOf())
					cls='dhx_now';
				html+=" class='"+cls+" "+this.templates.month_date_class(sd,cd)+"' ";
				html+="><div class='dhx_month_head'>"+this.templates.month_day(sd)+"</div><div class='dhx_month_body' "+tdcss[j]+"></div></td>";
				sd=this.date.add(sd,1,"day");
			}
		html+="</tr>";
		h[i] = cellheight;
		cellheight+=this._colsS.height;
	}
	html+="</table>";
	this._max_date=sd;
	
	b.innerHTML=html;	
	return sd;
};
scheduler.getLabel = function(property, key) {
	var sections = this.config.lightbox.sections;
	for (var i=0; i<sections.length; i++) {
		if(sections[i].map_to == property) {
			var options = sections[i].options;
			for (var j=0; j<options.length; j++) {
				if(options[j].key == key) {
					return options[j].label;
				}
			}
		}
	}
	return "";
};
scheduler.updateCollection = function(list_name, collection){
    var list = scheduler.serverList(list_name);
    if(!list) return false;
    list.splice(0,list.length);
    list.push.apply(list, collection||[]);
    scheduler.callEvent("onOptionsLoad", []);
    scheduler.resetLightbox();
    return true;
};
scheduler._lame_copy=function(target, source){
    for(var key in source)
        target[key] = source[key];
    return target;
};
