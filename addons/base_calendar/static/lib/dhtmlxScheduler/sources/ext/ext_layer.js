/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTemplatesReady",function(){

	this.layers.sort(function(a, b){
		return a.zIndex - b.zIndex;
	});
	
	scheduler._dp_init=function(dp){
		dp._methods=["setEventTextStyle","","changeEventId","deleteEvent"];
		
		this.attachEvent("onEventAdded",function(id){
			if (!this._loading && this.validId(id) && this.getEvent(id) && this.getEvent(id).layer == dp.layer)
				dp.setUpdated(id,true,"inserted");
		});
		this.attachEvent("onBeforeEventDelete",function(id){
			if(this.getEvent(id) && this.getEvent(id).layer == dp.layer) {
				if (!this.validId(id)) return;
				  var z=dp.getState(id);
				  
				if (z=="inserted" || this._new_event) {  dp.setUpdated(id,false);		return true; }
				if (z=="deleted")  return false;
				if (z=="true_deleted")  return true;
				
				dp.setUpdated(id,true,"deleted");
					return false;				
			}
			else return true;
		});
		this.attachEvent("onEventChanged",function(id){
			if (!this._loading && this.validId(id) && this.getEvent(id) && this.getEvent(id).layer == dp.layer)
				dp.setUpdated(id,true,"updated");
		});
		
		dp._getRowData=function(id,pref){
			var ev=this.obj.getEvent(id);
			var data = {};
			
			for (var a in ev){
				if (a.indexOf("_")==0) continue;
				if (ev[a] && ev[a].getUTCFullYear) //not very good, but will work
					data[a] = this.obj.templates.xml_format(ev[a]);
				else
					data[a] = ev[a];
			}
			return data;
		};
		dp._clearUpdateFlag=function(){};
		
		dp.attachEvent("insertCallback", scheduler._update_callback);
		dp.attachEvent("updateCallback", scheduler._update_callback);
		dp.attachEvent("deleteCallback", function(upd, id) {
			this.obj.setUserData(id, this.action_param, "true_deleted");
			this.obj.deleteEvent(id);
		});	
	};

	(function() {
        var _cloneObj = function(obj){
            if(obj == null || typeof(obj) != 'object')
                return obj;
            var temp = new obj.constructor();
            for(var key in obj)
                temp[key] = _cloneObj(obj[key]);
            return temp;
        };
        
		scheduler._dataprocessors = [];
		scheduler._layers_zindex = {};
		for(var i=0; i<scheduler.layers.length; i++) {
			scheduler.config['lightbox_'+scheduler.layers[i].name] = { };
            scheduler.config['lightbox_'+scheduler.layers[i].name].sections = _cloneObj(scheduler.config.lightbox.sections);
			scheduler._layers_zindex[scheduler.layers[i].name] = scheduler.config.inital_layer_zindex||5 + i*3;
			if(scheduler.layers[i].url) {
				var dp = new dataProcessor(scheduler.layers[i].url);
				dp.layer = scheduler.layers[i].name;
				scheduler._dataprocessors.push(dp);
				scheduler._dataprocessors[i].init(scheduler);
			}
			if(scheduler.layers[i].isDefault)
				scheduler.defaultLayer = scheduler.layers[i].name;
		}
	})();

	
	scheduler.showLayer = function(tlayer) {
		this.toggleLayer(tlayer, true);
	};
	
	scheduler.hideLayer = function(tlayer) {
		this.toggleLayer(tlayer, false);
	};
	
	scheduler.toggleLayer = function(tlayer, visible) { // visible is optional
		var layer = this.getLayer(tlayer);
		
		if(typeof visible != 'undefined')
			layer.visible = !!visible;
		else
			layer.visible = !layer.visible;
			
		this.setCurrentView(this._date, this._mode);
	};
	
	scheduler.getLayer = function(tlayer) { // either string with layer name or event with layer property
		if(typeof tlayer == 'string') 
			var layer_name = tlayer;
		if(typeof tlayer == 'object') 
			var layer_name = tlayer.layer;
		var layer;
		for (var i=0; i<scheduler.layers.length; i++) {
			if(scheduler.layers[i].name == layer_name)
				layer = scheduler.layers[i];
		}	
		return layer;
	};

	scheduler.attachEvent("onBeforeLightbox", function (event_id){
		var ev = this.getEvent(event_id);
        this.config.lightbox.sections = this.config['lightbox_'+ev.layer].sections;
        scheduler.resetLightbox();
		return true;
	});

	scheduler.attachEvent("onClick", function (event_id, native_event_object){
		var ev = scheduler.getEvent(event_id);
        return !scheduler.getLayer(ev.layer).noMenu;
	});	
	
	scheduler.attachEvent('onEventCollision', function(ev, evs) {
		var layer = this.getLayer(ev);
		if(!layer.checkCollision)
			return false;
		var count = 0;
		for(var i = 0; i<evs.length; i++) {
			if(evs[i].layer == layer.name && evs[i].id != ev.id)
				count++;
		}
		return (count >= scheduler.config.collision_limit);
	});
	
	scheduler.addEvent=function(start_date,end_date,text,id,extra_data){
		var ev=start_date;
		if (arguments.length!=1){
			ev=extra_data||{};
			ev.start_date=start_date;
			ev.end_date=end_date;
			ev.text=text;
			ev.id=id;
			ev.layer = this.defaultLayer;
		};
		ev.id = ev.id||scheduler.uid();
		ev.text = ev.text||"";
		
		
		if (typeof ev.start_date == "string")  ev.start_date=this.templates.api_date(ev.start_date);
		if (typeof ev.end_date == "string")  ev.end_date=this.templates.api_date(ev.end_date);
		ev._timed=this.is_one_day_event(ev);

		var is_new=!this._events[ev.id];
		this._events[ev.id]=ev;
		this.event_updated(ev);
		if (!this._loading)
			this.callEvent(is_new?"onEventAdded":"onEventChanged",[ev.id,ev]);
	};		
	
	this._evs_layer = {};
	for (var i = 0; i < this.layers.length; i++) { // array in object for each layer
		this._evs_layer[this.layers[i].name] = [];
	}		
	
	scheduler.addEventNow=function(start,end,e){
		var base = {};
		if (typeof start == "object"){
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
		
		
		base.start_date = base.start_date||start_date;
		base.end_date =  base.end_date||new Date(end);
		base.text = base.text||this.locale.labels.new_event;
		base.id = this._drag_id = this.uid();
		base.layer = this.defaultLayer;
		this._drag_mode="new-size";
		
		this._loading=true;
		this.addEvent(base);
		this.callEvent("onEventCreated",[this._drag_id,e]);
		this._loading=false;
		
		this._drag_event={}; //dummy , to trigger correct event updating logic
		this._on_mouse_up(e);	
	}	
	
	scheduler._t_render_view_data = function(events) { // helper
		if (this.config.multi_day && !this._table_view) {
			var tvs = [];
			var tvd = [];
			for (var k = 0; k < events.length; k++) {
				if (events[k]._timed) 
					tvs.push(events[k]);
				else 
					tvd.push(events[k]);
			}
			this._table_view = true;
			this.render_data(tvd);
			this._table_view = false;
			this.render_data(tvs);
		}
		else 
			this.render_data(events);		
	};
	
	scheduler.render_view_data = function(){
		if (this._not_render) {
			this._render_wait = true;
			return;
		}
		this._render_wait = false;
		
		this.clear_view();

		this._evs_layer = {};
		for (var i = 0; i < this.layers.length; i++) { // array in object for each layer
			this._evs_layer[this.layers[i].name] = [];
		}		
		
		var evs = this.get_visible_events();
		for (var i = 0; i < evs.length; i++) { // filling layer arrays with events
			if(this._evs_layer[evs[i].layer])
				this._evs_layer[evs[i].layer].push(evs[i]);
		}			

		if(this._mode == 'month') { // old logic is used
			var tevs = [];
			for (var i = 0; i < this.layers.length; i++) {
				if (this.layers[i].visible) 
					tevs = tevs.concat(this._evs_layer[this.layers[i].name]);
			}
			this._t_render_view_data(tevs);
		}
		else { // week, day; should use new logic
			for (var i = 0; i < this.layers.length; i++) {
				if (this.layers[i].visible) {
					var evs_layer = this._evs_layer[this.layers[i].name];
					this._t_render_view_data(evs_layer);
				}
			}
		}
	};
	
	scheduler._render_v_bar=function(id,x,y,w,h,style,contentA,contentB,bottom){
		var ev = this.getEvent(id);
		if(contentA.indexOf('<div class=') == -1)
			contentA = (scheduler.templates['event_header_'+ev.layer])?scheduler.templates['event_header_'+ev.layer](ev.start_date,ev.end_date,ev):contentA;
		if(contentB.indexOf('<div class=') == -1)	
		contentB = (scheduler.templates['event_text_'+ev.layer])?scheduler.templates['event_text_'+ev.layer](ev.start_date,ev.end_date,ev):contentB;
		
		var d=document.createElement("DIV");
		
		
		var cs = "dhx_cal_event";
		var cse = (scheduler.templates['event_class_'+ev.layer])?scheduler.templates['event_class_'+ev.layer](ev.start_date,ev.end_date,ev):scheduler.templates.event_class(ev.start_date,ev.end_date,ev);
		if (cse) cs=cs+" "+cse;
		
		var html='<div event_id="'+id+'" class="'+cs+'" style="position:absolute; top:'+y+'px; left:'+x+'px; width:'+(w-4)+'px; height:'+h+'px;'+(style||"")+'">';
		html+='<div class="dhx_header" style=" width:'+(w-6)+'px;" >&nbsp;</div>';
		html+='<div class="dhx_title">'+contentA+'</div>';
		html+='<div class="dhx_body" style=" width:'+(w-(this._quirks?4:14))+'px; height:'+(h-(this._quirks?20:30))+'px;">'+contentB+'</div>';
		html+='<div class="dhx_footer" style=" width:'+(w-8)+'px;'+(bottom?' margin-top:-1px;':'')+'" ></div></div>';
		
		d.innerHTML=html;
		d.style.zIndex = 100;
		return d.firstChild;
	};	
	
	scheduler.render_event_bar=function(ev){
		var parent=this._els["dhx_cal_data"][0];

		var x=this._colsS[ev._sday];
		var x2=this._colsS[ev._eday];
		if (x2==x) x2=this._colsS[ev._eday+1];
		var hb = this.xy.bar_height;
		
		var y=this._colsS.heights[ev._sweek]+(this._colsS.height?(this.xy.month_scale_height+2):2)+ev._sorder*hb; 
				
		var d=document.createElement("DIV");
		var cs = ev._timed?"dhx_cal_event_clear":"dhx_cal_event_line";
		var cse = (scheduler.templates['event_class_'+ev.layer])?scheduler.templates['event_class_'+ev.layer](ev.start_date,ev.end_date,ev):scheduler.templates.event_class(ev.start_date,ev.end_date,ev);
		if (cse) cs=cs+" "+cse; 
		
		var html='<div event_id="'+ev.id+'" class="'+cs+'" style="position:absolute; top:'+y+'px; left:'+x+'px; width:'+(x2-x-15)+'px;'+(ev._text_style||"")+'">';
			
		if (ev._timed)
			html+=(scheduler.templates['event_bar_date_'+ev.layer])?scheduler.templates['event_bar_date_'+ev.layer](ev.start_date,ev.end_date,ev):scheduler.templates.event_bar_date(ev.start_date,ev.end_date,ev);
		html+=( (scheduler.templates['event_bar_text_'+ev.layer])?scheduler.templates['event_bar_text_'+ev.layer](ev.start_date,ev.end_date,ev):scheduler.templates.event_bar_text(ev.start_date,ev.end_date,ev) + '</div>)');
		html+='</div>';
		
		d.innerHTML=html;
		
		this._rendered.push(d.firstChild);
		parent.appendChild(d.firstChild);
	};	

	scheduler.render_event=function(ev){
		var menu = scheduler.xy.menu_width;
		if(scheduler.getLayer(ev.layer).noMenu) 
			menu = 0;
		
		if (ev._sday<0) return; //can occur in case of recurring event during time shift
		var parent=scheduler.locate_holder(ev._sday);	
		if (!parent) return; //attempt to render non-visible event
		var sm = ev.start_date.getHours()*60+ev.start_date.getMinutes();
		var em = (ev.end_date.getHours()*60+ev.end_date.getMinutes())||(scheduler.config.last_hour*60);
		
		var top = (Math.round((sm*60*1000-this.config.first_hour*60*60*1000)*this.config.hour_size_px/(60*60*1000)))%(this.config.hour_size_px*24)+1; //42px/hour
		var height = Math.max(scheduler.xy.min_event_height,(em-sm)*this.config.hour_size_px/60)+1; //42px/hour
		//var height = Math.max(25,Math.round((ev.end_date.valueOf()-ev.start_date.valueOf())*(this.config.hour_size_px+(this._quirks?1:0))/(60*60*1000))); //42px/hour
		var width=Math.floor((parent.clientWidth-menu)/ev._count);
		var left=ev._sorder*width+1;
		if (!ev._inner) width=width*(ev._count-ev._sorder);
		
		
		
		var d=this._render_v_bar(ev.id,menu+left,top,width,height,ev._text_style,scheduler.templates.event_header(ev.start_date,ev.end_date,ev),scheduler.templates.event_text(ev.start_date,ev.end_date,ev));
			
		this._rendered.push(d);
		parent.appendChild(d);
		
		left=left+parseInt(parent.style.left,10)+menu;
		
		top+=this._dy_shift; //corrupt top, to include possible multi-day shift
		d.style.zIndex = this._layers_zindex[ev.layer];
		
		if (this._edit_id==ev.id){
			d.style.zIndex = parseInt(d.style.zIndex)+1; //fix overlapping issue
			var new_zIndex = d.style.zIndex;
			width=Math.max(width-4,scheduler.xy.editor_width);
			var d=document.createElement("DIV");
			d.setAttribute("event_id",ev.id);
			this.set_xy(d,width,height-20,left,top+14);
			d.className="dhx_cal_editor";
			d.style.zIndex = new_zIndex;
			var d2=document.createElement("DIV");
			this.set_xy(d2,width-6,height-26);
			d2.style.cssText+=";margin:2px 2px 2px 2px;overflow:hidden;";
			
			
			d2.style.zIndex = new_zIndex;
			d.appendChild(d2);
			this._els["dhx_cal_data"][0].appendChild(d);
			this._rendered.push(d);
		
			d2.innerHTML="<textarea class='dhx_cal_editor'>"+ev.text+"</textarea>";
			if (this._quirks7) d2.firstChild.style.height=height-12+"px"; //IEFIX
			this._editor=d2.firstChild;
			this._editor.onkeypress=function(e){ 
				if ((e||event).shiftKey) return true;
				var code=(e||event).keyCode; 
				if (code==scheduler.keys.edit_save) scheduler.editStop(true); 
				if (code==scheduler.keys.edit_cancel) scheduler.editStop(false); 
			};
			this._editor.onselectstart=function(e){ return (e||event).cancelBubble=true; };
			d2.firstChild.focus();
			//IE and opera can add x-scroll during focusing
			this._els["dhx_cal_data"][0].scrollLeft=0;
			d2.firstChild.select();
		}
		if (this._select_id==ev.id){
			d.style.zIndex = parseInt(d.style.zIndex)+1; //fix overlapping issue
			var icons=this.config["icons_"+((this._edit_id==ev.id)?"edit":"select")];
			var icons_str="";
			for (var i=0; i<icons.length; i++)
				icons_str+="<div class='dhx_menu_icon "+icons[i]+"' title='"+this.locale.labels[icons[i]]+"'></div>";
			var obj = this._render_v_bar(ev.id,left-menu+1,top,menu,icons.length*20+26,"","<div class='dhx_menu_head'></div>",icons_str,true);
			obj.style.left=left-menu+1;
			obj.style.zIndex = d.style.zIndex;
			this._els["dhx_cal_data"][0].appendChild(obj);
			this._rendered.push(obj);
		}
		
	};

    scheduler.filter_agenda = function(id, event) {
        var layer = scheduler.getLayer(event.layer);
        return (layer && layer.visible);
    };
});
