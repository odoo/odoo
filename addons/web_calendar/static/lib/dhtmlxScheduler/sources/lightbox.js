/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.formSection = function(name){
	var config = this.config.lightbox.sections;
	var i =0;
	for (i; i < config.length; i++)
		if (config[i].name == name)
			break;
	var section = config[i];
	var node = document.getElementById(section.id).nextSibling;

	return {
		getValue:function(ev){
			return scheduler.form_blocks[section.type].get_value(node, (ev||{}), section);
		},
		setValue:function(value, ev){
			return scheduler.form_blocks[section.type].set_value(node, value, (ev||{}), section);
		}
	};
};
scheduler.form_blocks={
    template:{
        render: function(sns){
        	var height=(sns.height||"30")+"px";
            return "<div class='dhx_cal_ltext dhx_cal_template' style='height:"+height+";'></div>";
        },
        set_value:function(node,value,ev,config){ 
            node.innerHTML = value||"";
        },
        get_value:function(node,ev,config){
            return node.innerHTML||"";
        },
        focus: function(node){
        }
    },
	textarea:{
		render:function(sns){
			var height=(sns.height||"130")+"px";
			return "<div class='dhx_cal_ltext' style='height:"+height+";'><textarea></textarea></div>";
		},
		set_value:function(node,value,ev){
			node.firstChild.value=value||"";
		},
		get_value:function(node,ev){
			return node.firstChild.value;
		},
		focus:function(node){
			var a=node.firstChild; a.select(); a.focus(); 
		}
	},
	select:{
		render:function(sns){
			var height=(sns.height||"23")+"px";
			var html="<div class='dhx_cal_ltext' style='height:"+height+";'><select style='width:100%;'>";
			for (var i=0; i < sns.options.length; i++)
				html+="<option value='"+sns.options[i].key+"'>"+sns.options[i].label+"</option>";
			html+="</select></div>";
			return html;
		},
		set_value:function(node,value,ev){
			if (typeof value == "undefined")
				value = (node.firstChild.options[0]||{}).value;
			node.firstChild.value=value||"";
		},
		get_value:function(node,ev){
			return node.firstChild.value;
		},
		focus:function(node){
			var a=node.firstChild; if (a.select) a.select(); a.focus(); 
		}
	},	
	time:{
		render:function(){
			//hours
			var cfg = scheduler.config;
			var dt = this.date.date_part(new Date());
			var last = 24*60, first = 0;
			if(scheduler.config.limit_time_select){
				last = 60*cfg.last_hour+1;
				first = 60*cfg.first_hour;
				dt.setHours(cfg.first_hour);
			}
				
			var html="<select>";
			var i = first;
			var tdate = dt.getDate();

			while(i<last){
				var time=this.templates.time_picker(dt);
				html+="<option value='"+i+"'>"+time+"</option>";

				dt.setTime(dt.valueOf()+this.config.time_step*60*1000);
                var diff = (dt.getDate()!=tdate)?1:0; // moved or not to the next day
                i=diff*24*60+dt.getHours()*60+dt.getMinutes();
			}
			
			//days
			html+="</select> <select>";
			for (var i=1; i < 32; i++) 
				html+="<option value='"+i+"'>"+i+"</option>";
			
			//month
			html+="</select> <select>";
			for (var i=0; i < 12; i++) 
				html+="<option value='"+i+"'>"+this.locale.date.month_full[i]+"</option>";
			
			//year
			html+="</select> <select>";
			dt = dt.getFullYear()-5; //maybe take from config?
			for (var i=0; i < 10; i++) 
				html+="<option value='"+(dt+i)+"'>"+(dt+i)+"</option>";
			html+="</select> ";
			
			return "<div style='height:30px;padding-top:0px;font-size:inherit;' class='dhx_section_time'>"+html+"<span style='font-weight:normal; font-size:10pt;'> &nbsp;&ndash;&nbsp; </span>"+html+"</div>";			

		},
		set_value:function(node,value,ev){


			var s=node.getElementsByTagName("select");

			if(scheduler.config.full_day) {
				if (!node._full_day){
					var html = "<label class='dhx_fullday'><input type='checkbox' name='full_day' value='true'> "+scheduler.locale.labels.full_day+"&nbsp;</label></input>";
					if (!scheduler.config.wide_form)
						html = node.previousSibling.innerHTML+html;
					node.previousSibling.innerHTML=html;
					node._full_day=true;
				}
				var input=node.previousSibling.getElementsByTagName("input")[0];
				var isFulldayEvent = (scheduler.date.time_part(ev.start_date)===0 && scheduler.date.time_part(ev.end_date)===0 && ev.end_date.valueOf()-ev.start_date.valueOf() < 2*24*60*60*1000);
				input.checked = isFulldayEvent;
				
				for(var k in s)
					s[k].disabled=input.checked;

				input.onclick = function(){ 
					if(input.checked) {
						var start_date = new Date(ev.start_date);
						var end_date = new Date(ev.end_date);
						
						scheduler.date.date_part(start_date);
						end_date = scheduler.date.add(start_date, 1, "day");
					} 
					for(var i in s)
						s[i].disabled=input.checked;
					
					_fill_lightbox_select(s,0,start_date||ev.start_date);
					_fill_lightbox_select(s,4,end_date||ev.end_date);
				};
			}
			
			if(scheduler.config.auto_end_date && scheduler.config.event_duration) {
				function _update_lightbox_select() {
					ev.start_date=new Date(s[3].value,s[2].value,s[1].value,0,s[0].value);
					ev.end_date.setTime(ev.start_date.getTime() + (scheduler.config.event_duration * 60 * 1000));
					_fill_lightbox_select(s,4,ev.end_date);
				}
				for(var i=0; i<4; i++) {
					s[i].onchange = _update_lightbox_select;
				}
			}
			
			function _fill_lightbox_select(s,i,d){
				s[i+0].value=Math.round((d.getHours()*60+d.getMinutes())/scheduler.config.time_step)*scheduler.config.time_step;	
				s[i+1].value=d.getDate();
				s[i+2].value=d.getMonth();
				s[i+3].value=d.getFullYear();
			}
			
			_fill_lightbox_select(s,0,ev.start_date);
			_fill_lightbox_select(s,4,ev.end_date);
		},
		get_value:function(node,ev){
			s=node.getElementsByTagName("select");
			ev.start_date=new Date(s[3].value,s[2].value,s[1].value,0,s[0].value);
			ev.end_date=new Date(s[7].value,s[6].value,s[5].value,0,s[4].value);
			if (ev.end_date<=ev.start_date) 
				ev.end_date=scheduler.date.add(ev.start_date,scheduler.config.time_step,"minute");
		},
		focus:function(node){
			node.getElementsByTagName("select")[0].focus(); 
		}
	}
};
scheduler.showCover=function(box){
	if (box){
		box.style.display="block";

		var scroll_top = window.pageYOffset||document.body.scrollTop||document.documentElement.scrollTop;
		var scroll_left = window.pageXOffset||document.body.scrollLeft||document.documentElement.scrollLeft;

        var view_height = window.innerHeight||document.documentElement.clientHeight;

        if(scroll_top) // if vertical scroll on window
			box.style.top=Math.round(scroll_top+Math.max((view_height-box.offsetHeight)/2, 0))+"px";
		else // vertical scroll on body
			box.style.top=Math.round(Math.max(((view_height-box.offsetHeight)/2), 0) + 9)+"px"; // +9 for compatibility with auto tests

		// not quite accurate but used for compatibility reasons
		if(document.documentElement.scrollWidth > document.body.offsetWidth) // if horizontal scroll on the window
			box.style.left=Math.round(scroll_left+(document.body.offsetWidth-box.offsetWidth)/2)+"px";
		else // horizontal scroll on the body
			box.style.left=Math.round((document.body.offsetWidth-box.offsetWidth)/2)+"px";
	}
    this.show_cover();
};
scheduler.showLightbox=function(id){
	if (!id) return;
	if (!this.callEvent("onBeforeLightbox",[id])) return;
	var box = this._get_lightbox();
	this.showCover(box);
	this._fill_lightbox(id,box);
	this.callEvent("onLightbox",[id]);
};
scheduler._fill_lightbox=function(id,box){ 
	var ev=this.getEvent(id);
	var s=box.getElementsByTagName("span");
	if (scheduler.templates.lightbox_header){
		s[1].innerHTML="";
		s[2].innerHTML=scheduler.templates.lightbox_header(ev.start_date,ev.end_date,ev);
	} else {
		s[1].innerHTML=this.templates.event_header(ev.start_date,ev.end_date,ev);
		s[2].innerHTML=(this.templates.event_bar_text(ev.start_date,ev.end_date,ev)||"").substr(0,70); //IE6 fix	
	}
	
	
	var sns = this.config.lightbox.sections;	
	for (var i=0; i < sns.length; i++) {
		var node=document.getElementById(sns[i].id).nextSibling;
		var block=this.form_blocks[sns[i].type];
		block.set_value.call(this,node,ev[sns[i].map_to],ev, sns[i]);
		if (sns[i].focus)
			block.focus.call(this,node);
	}
	
	scheduler._lightbox_id=id;
};
scheduler._lightbox_out=function(ev){
	var sns = this.config.lightbox.sections;	
	for (var i=0; i < sns.length; i++) {
        var node = document.getElementById(sns[i].id);
		node=(node?node.nextSibling:node);
		var block=this.form_blocks[sns[i].type];
		var res=block.get_value.call(this,node,ev, sns[i]);
		if (sns[i].map_to!="auto")
			ev[sns[i].map_to]=res;
	}
	return ev;
};
scheduler._empty_lightbox=function(){
	var id=scheduler._lightbox_id;
	var ev=this.getEvent(id);
	var box=this._get_lightbox();
	
	this._lightbox_out(ev);
	
	ev._timed=this.is_one_day_event(ev);
	this.setEvent(ev.id,ev);
	this._edit_stop_event(ev,true);
	this.render_view_data();
};
scheduler.hide_lightbox=function(id){
	this.hideCover(this._get_lightbox());
	this._lightbox_id=null;
	this.callEvent("onAfterLightbox",[]);
};
scheduler.hideCover=function(box){
	if (box) box.style.display="none";
	this.hide_cover();
};
scheduler.hide_cover=function(){
	if (this._cover) 
		this._cover.parentNode.removeChild(this._cover);
	this._cover=null;
};
scheduler.show_cover=function(){
	this._cover=document.createElement("DIV");
	this._cover.className="dhx_cal_cover";
	var _document_height = ((document.height !== undefined) ? document.height : document.body.offsetHeight);
	var _scroll_height = ((document.documentElement) ? document.documentElement.scrollHeight : 0);
	this._cover.style.height = Math.max(_document_height, _scroll_height) + 'px';
	document.body.appendChild(this._cover);
};
scheduler.save_lightbox=function(){
	if (this.checkEvent("onEventSave") && !this.callEvent("onEventSave",[this._lightbox_id,this._lightbox_out({ id: this._lightbox_id}), this._new_event]))
		return;
	this._empty_lightbox();
	this.hide_lightbox();
};
scheduler.startLightbox = function(id, box){
	this._lightbox_id=id;
	this.showCover(box);
};
scheduler.endLightbox = function(mode, box){
	this._edit_stop_event(scheduler.getEvent(this._lightbox_id),mode);
	if (mode)
		scheduler.render_view_data();
	this.hideCover(box);
};
scheduler.resetLightbox = function(){
	if (scheduler._lightbox) 
		scheduler._lightbox.parentNode.removeChild(scheduler._lightbox);
	scheduler._lightbox = null;
};
scheduler.cancel_lightbox=function(){
	this.callEvent("onEventCancel",[this._lightbox_id, this._new_event]);
	this.endLightbox(false);
	this.hide_lightbox();
};
scheduler._init_lightbox_events=function(){
	this._get_lightbox().onclick=function(e){
		var src=e?e.target:event.srcElement;
		if (!src.className) src=src.previousSibling;
		if (src && src.className)
			switch(src.className){
				case "dhx_save_btn":
					scheduler.save_lightbox();
					break;
				case "dhx_delete_btn":
					var c=scheduler.locale.labels.confirm_deleting; 
					if (!c||confirm(c)) {
						scheduler.deleteEvent(scheduler._lightbox_id);
						scheduler._new_event = null; //clear flag, if it was unsaved event
						scheduler.hide_lightbox();
					}
					break;
				case "dhx_cancel_btn":
					scheduler.cancel_lightbox();
					break;
					
				default:
					if (src.getAttribute("dhx_button")){
						scheduler.callEvent("onLightboxButton", [src.className, src, e]);
					} else if (src.className.indexOf("dhx_custom_button_")!=-1){
						var index = src.parentNode.getAttribute("index");
						var block=scheduler.form_blocks[scheduler.config.lightbox.sections[index].type];
						var sec = src.parentNode.parentNode;
						block.button_click(index,src,sec,sec.nextSibling);	
					}
					break;
			}
	};
	this._get_lightbox().onkeydown=function(e){
		switch((e||event).keyCode){
			case scheduler.keys.edit_save:
				if ((e||event).shiftKey) return;
				scheduler.save_lightbox();
				break;
			case scheduler.keys.edit_cancel:
				scheduler.cancel_lightbox();
				break;
			default:
				break;
		}
	};
};
scheduler.setLightboxSize=function(){
	var d = this._lightbox;
	if (!d) return;
	
	var con = d.childNodes[1];
	con.style.height="0px";
	con.style.height=con.scrollHeight+"px";		
	d.style.height=con.scrollHeight+50+"px";		
	con.style.height=con.scrollHeight+"px";		 //it is incredible , how ugly IE can be 	
};

scheduler._init_dnd_events = function(){
	dhtmlxEvent(document.body, "mousemove", scheduler._move_while_dnd);
	dhtmlxEvent(document.body, "mouseup", scheduler._finish_dnd);
	scheduler._init_dnd_events = function(){};
};
scheduler._move_while_dnd = function(e){
	if (scheduler._dnd_start_lb){
		if (!document.dhx_unselectable){
			document.body.className += " dhx_unselectable";
			document.dhx_unselectable = true;
		}
		var lb = scheduler._get_lightbox();	
		var now = (e&&e.target)?[e.pageX, e.pageY]:[event.clientX, event.clientY];
		lb.style.top = scheduler._lb_start[1]+now[1]-scheduler._dnd_start_lb[1]+"px";
		lb.style.left = scheduler._lb_start[0]+now[0]-scheduler._dnd_start_lb[0]+"px";
	}
};
scheduler._ready_to_dnd = function(e){
	var lb = scheduler._get_lightbox();
	scheduler._lb_start = [parseInt(lb.style.left,10), parseInt(lb.style.top,10)];
	scheduler._dnd_start_lb = (e&&e.target)?[e.pageX, e.pageY]:[event.clientX, event.clientY];
};
scheduler._finish_dnd = function(){
	if (scheduler._lb_start){
		scheduler._lb_start = scheduler._dnd_start_lb = false;
		document.body.className = document.body.className.replace(" dhx_unselectable","");
		document.dhx_unselectable = false;
	}
};
scheduler._get_lightbox=function(){ //scheduler.config.wide_form=true;
	if (!this._lightbox){
		var d=document.createElement("DIV");
		d.className="dhx_cal_light";
		if (scheduler.config.wide_form)
			d.className+=" dhx_cal_light_wide";
		if (scheduler.form_blocks.recurring)
			d.className+=" dhx_cal_light_rec";
			
		if (/msie|MSIE 6/.test(navigator.userAgent))
			d.className+=" dhx_ie6";
		d.style.visibility="hidden";
		var html = this._lightbox_template
		var buttons = this.config.buttons_left;
		scheduler.locale.labels["dhx_save_btn"] = scheduler.locale.labels.icon_save;
		scheduler.locale.labels["dhx_cancel_btn"] = scheduler.locale.labels.icon_cancel;
		scheduler.locale.labels["dhx_delete_btn"] = scheduler.locale.labels.icon_delete;
		for (var i = 0; i < buttons.length; i++)
			html+="<div class='dhx_btn_set'><div dhx_button='1' class='"+buttons[i]+"'></div><div>"+scheduler.locale.labels[buttons[i]]+"</div></div>";
		buttons = this.config.buttons_right;
		for (var i = 0; i < buttons.length; i++)
			html+="<div class='dhx_btn_set' style='float:right;'><div dhx_button='1' class='"+buttons[i]+"'></div><div>"+scheduler.locale.labels[buttons[i]]+"</div></div>";
		
		html+="</div>";
		d.innerHTML=html;
		if (scheduler.config.drag_lightbox){
			d.firstChild.onmousedown = scheduler._ready_to_dnd;
			d.firstChild.onselectstart = function(){ return false; };
			d.firstChild.style.cursor = "pointer";
			scheduler._init_dnd_events();
			
		}
		document.body.insertBefore(d,document.body.firstChild);
		this._lightbox=d;
		
		var sns=this.config.lightbox.sections;
		html="";
		for (var i=0; i < sns.length; i++) {
			var block=this.form_blocks[sns[i].type];
			if (!block) continue; //ignore incorrect blocks
			sns[i].id="area_"+this.uid();
			var button = "";
			if (sns[i].button){
			 	button = "<div class='dhx_custom_button' index='"+i+"'><div class='dhx_custom_button_"+sns[i].button+"'></div><div>"+this.locale.labels["button_"+sns[i].button]+"</div></div>";
			 }
			
			if (this.config.wide_form){
				html+="<div class='dhx_wrap_section'>";
			}
			html+="<div id='"+sns[i].id+"' class='dhx_cal_lsection'>"+button+this.locale.labels["section_"+sns[i].name]+"</div>"+block.render.call(this,sns[i]);
			html+="</div>"
		}
		
		//localization
		var ds=d.getElementsByTagName("div");
		//sections
		ds[1].innerHTML=html;
		//sizes
		this.setLightboxSize();
	
		this._init_lightbox_events(this);
		d.style.display="none";
		d.style.visibility="visible";
	}
	return this._lightbox;
};
scheduler._lightbox_template="<div class='dhx_cal_ltitle'><span class='dhx_mark'>&nbsp;</span><span class='dhx_time'></span><span class='dhx_title'></span></div><div class='dhx_cal_larea'></div>";
