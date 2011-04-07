TouchScroll=function(node, nontouch, scroll, compat){
	this.debug =  !!nontouch;
	this.compat = !!compat;
	this.rough =  !!scroll;


	this.axisX = this.axisY = true;
	
	if (typeof node!= "object")
		node = document.getElementById(node);

	this._init();
	node.addEventListener("touchstart",this,false);
	node.addEventListener("webkitTransitionEnd",this,false);
	if (this.debug)
		node.addEventListener("mousedown",this,false);
		
		
	this.node = node;
	for (var i=0; i < node.childNodes.length; i++)
		if (node.childNodes[i].nodeType == 1){
			this.area = node.childNodes[i];
			break;
		}

	if (window.getComputedStyle(this.node).position == "static")
		this.node.style.position = "relative"
	this.area.style.cssText += "-webkit-transition: -webkit-transform; -webkit-user-select:none; -webkit-transform-style:preserve-3d;";
	this.scrolls={};
};

TouchScroll.prototype = {
	refresh:function(){
		this.node.style.webkitTransformStyle="flat";
		this.node.style.webkitTransformStyle="preserve-3d";
	},
	scrollTo:function(x,y,speed){
		this.set_matrix({e:x,f:y}, (speed||0));
	},
	onscroll:function(x,y){}, 
	handleEvent:function(ev){
		return this["ev_"+ev.type](ev);
	},
	get_matrix:function(node){
		return new WebKitCSSMatrix(window.getComputedStyle(node||this.area).webkitTransform);
	},
	set_matrix:function(value,speed,node){
		(node||this.area).style.webkitTransform = "translate("+Math.round(value.e)+"px,"+Math.round(value.f)+"px)";
		(node||this.area).style.webkitTransitionDuration= speed;
	},
	ev_touchstart:function(ev){ 
		this.ev_mousedown(ev.touches[0]);
		ev.preventDefault();
		return false;
	},
	ev_mousedown:function(ev){
		var touch  = ev;

		this.x = touch.pageX;
		this.y = touch.pageY;
		this.dx = this.node.offsetWidth;
		this.dy = this.node.offsetHeight;
		this.mx = this.area.scrollWidth;
		this.my = this.area.scrollHeight;
		this.target = touch.target;
		
		if (!this.rough){
			var temp = this.get_matrix();
			this.target_x = temp.e;
			this.target_y = temp.f;
			if (!this.scroll && this.compat){
				temp.e = this.node.scrollLeft*-1;
				temp.f = this.node.scrollTop*-1;
				this.node.scrollTop = this.node.scrollLeft = 0;
			} 
			
			this.set_matrix(temp,0);
			this._correct_scroll(this.target_x, this.target_y);
		}
		this.scroll_x = this.scroll_y = this.scroll = false;		
		
		
		this._init_events();
	},
	ev_touchend:function(){
		return this.ev_mouseup();
	},
	ev_mouseup:function(){
		this._deinit_events();
		if (!this.scroll){
			this._remove_scroll();
			var ev = document.createEvent("MouseEvent");
			ev.initMouseEvent("click",true, true);
			this.target.dispatchEvent(ev);
		} 
		this.target = null;
	},
	ev_webkitTransitionEnd:function(){
		if (this.target || !this.scroll) return;
		
		this._remove_scroll();
		var temp = this.get_matrix();
		this.node.firstChild._scrollTop = -1*temp.f;
			
		if (this.compat && (temp.e||temp.f)){ 
			var y = temp.f; var x = temp.e;
			temp.e = temp.f = 0;
			this.set_matrix(temp,0);
			
			this.node.scrollTop = -1*y;
			this.node.scrollLeft = -1*x;
		}
		
		this.scroll = false;
	},
	ev_touchmove:function(ev){
		return this.ev_mousemove(ev.touches[0]);
	},
	ev_mousemove:function(ev){
		if (!this.target) return;
		var touch = ev;
		
		var dx = (touch.pageX - this.x)*(this.axisX?5:0);//Math.min(3,this.mx/this.dx);
		var dy = (touch.pageY - this.y)*(this.axisY?5:0);//Math.min(3,this.my/this.dy);
		
		if (Math.abs(dx)<10 && Math.abs(dy)<10) return;
		
		if (Math.abs(dx)>50)
			this.scroll_x=true;
		if (Math.abs(dy)>50)
			this.scroll_y=true;
			
		
		if (this.scroll_x || this.scroll_y){
			this.x = touch.pageX; this.y = touch.pageY;
			this.scroll = true;
			var temp = this.get_matrix();
			dx = dx + (this.target_x - temp.e);
			dy = dy + (this.target_y - temp.f);
			
			var speed = "2000ms";
			var fast = "500ms";
			this.target_x = dx+temp.e;
			this.target_y = dy+temp.f;
			
			if (this.target_x > 0) {
				this.target_x = 0;
				speed = fast;
			}
			if (this.target_y > 0) {
				this.target_y = 0;
				speed = fast;
			}
			if (this.mx - this.dx + this.target_x < 0){
				this.target_x = - this.mx + this.dx;
				speed = fast;
			}
			if (this.my - this.dy + this.target_y < 0){
				this.target_y = - this.my + this.dy;
				speed = fast;
			}
		

			this.set_matrix({e:this.target_x,f:this.target_y},speed);
			this._add_scroll(temp.e, temp.f);
			this._correct_scroll(this.target_x, this.target_y, speed);
			this.onscroll(this.target_x, this.target_y);
		}
		return false;
	},
	_correct_scroll:function(x,y,speed){ 
		if (this.scrolls.x){
			var stemp = this.get_matrix(this.scrolls.x);
			var sx = this.dx*x/this.mx;
			this.set_matrix({e:-1*sx,f:0}, speed, this.scrolls.x);
		}
		if (this.scrolls.y){ 
			var stemp = this.get_matrix(this.scrolls.y);
			var sy = this.dy*y/this.my;
			this.set_matrix({e:0,f:-1*sy}, speed, this.scrolls.y);				
		}		
	},
	_remove_scroll:function(){
		if (this.scrolls.x)
			this.scrolls.x.parentNode.removeChild(this.scrolls.x);
		if (this.scrolls.y)	
			this.scrolls.y.parentNode.removeChild(this.scrolls.y);
		this.scrolls = {};
	},
	_add_scroll:function(){
		if (this.scrolls.ready) return;
		
		var d;
		if (this.my>5 && this.axisY){
			var h = this.dy*this.dy/this.my-1;
			this.scrolls.y = d = document.createElement("DIV");
			d.className="dhx_scroll_y";
			d.style.height = h +"px";
			this.node.appendChild(d);
		}
		if (this.mx>5 && this.axisX){
			var h = this.dx*this.dx/this.mx;
			this.scrolls.x = d = document.createElement("DIV");
			d.className="dhx_scroll_x";
			d.style.width = h +"px";
			this.node.appendChild(d);
		}
		
		var temp = this.get_matrix();
		this._correct_scroll(temp.e, temp.f, 0);
		this.scrolls.ready = true;
	},
	_init_events:function(){
		document.addEventListener("touchmove",this,false);	
		document.addEventListener("touchend",this,false);	
		if (this.debug){
			document.addEventListener("mousemove",this,false);	
			document.addEventListener("mouseup",this,false);	
		}
	},
	_deinit_events:function(){
		document.removeEventListener("touchmove",this,false);	
		document.removeEventListener("touchend",this,false);	
		if (this.debug){
			document.removeEventListener("mousemove",this,false);	
			document.removeEventListener("mouseup",this,false);	
		}
	},
	_init:function(){
		document.styleSheets[0].insertRule(".dhx_scroll_x { width:50px;height:4px;background:rgba(0, 0, 0, 0.4);position:absolute; left:0px; bottom:3px; border:1px solid transparent; -webkit-border-radius:4px;-webkit-transition: -webkit-transform;}",0);
		document.styleSheets[0].insertRule(".dhx_scroll_y { width:4px;height:50px;background:rgba(0, 0, 0, 0.4);position:absolute; top:0px; right:3px; border:1px solid transparent; -webkit-border-radius:4px;-webkit-transition: -webkit-transform;}",0);
		this._init = function(){};
	}
};





scheduler._ipad_before_init=function(){
	scheduler._ipad_before_init=function(){};
	scheduler.xy.scroll_width =  0;

	var tabs = scheduler._els["dhx_cal_tab"];
	var right = 42;
	for (var i=tabs.length-1; i >=0; i--) {
		tabs[i].style.cssText+="top:4px;";
		tabs[i].style.left="auto";
		tabs[i].style.right = right+"px";
		if (i==0)
			tabs[i].style.cssText+=";-webkit-border-top-left-radius: 5px; -webkit-border-bottom-left-radius: 5px;";
		if (i==tabs.length-1)
			tabs[i].style.cssText+=";-webkit-border-top-right-radius: 5px; -webkit-border-bottom-right-radius: 5px;";
		
		right+=100;
	};

	scheduler._els["dhx_cal_prev_button"][0].innerHTML = "&lt;";
	scheduler._els["dhx_cal_next_button"][0].innerHTML = "&gt;";
	var d = document.createElement("div");
	d.className = "dhx_cal_add_button";
	d.innerHTML = "+ ";
	d.onclick = function(){
		var now = new Date();
		if (now > scheduler._min_date && now < scheduler._max_date)
			scheduler.addEventNow();
		else
			scheduler.addEventNow(scheduler._min_date.valueOf());
	}
	scheduler._els["dhx_cal_navline"][0].appendChild(d);
	
	
	this._obj.onmousedown = this._obj.onmouseup = this._obj.onmousemove = function(){};
	
	var long_tap = null;
	var long_tap_pos = [];
	this._obj.ontouchmove=function(e){
		if (long_tap){
			var dx = Math.abs(e.touches[0].pageX - long_tap_pos[0]);
			var dy = Math.abs(e.touches[0].pageY - long_tap_pos[1]);
			if (dx>50 || dy>50)
				long_tap = window.clearTimeout(long_tap);
		}
		if (scheduler.config.touch_actions)
			scheduler._on_mouse_move(e.touches[0]);
	}
	this._obj.ontouchstart = function(e){
		if (scheduler._lightbox_id) return;
		
		long_tap = window.setTimeout(function(){
			scheduler._on_dbl_click(e.touches[0],(e.target.className?e.target:e.target.parentNode));
		},400);
		long_tap_pos = [e.touches[0].pageX, e.touches[0].pageY];
		if (scheduler.config.touch_actions)
			scheduler._on_mouse_down(e.touches[0]);
	}
	this._obj.ontouchend = function(e){
		if (long_tap)
			long_tap = window.clearTimeout(long_tap);
		if (scheduler.config.touch_actions)
			scheduler._on_mouse_up(e.touches[0]);
	}
}
scheduler._ipad_init=function(){
	var d = document.createElement("DIV");
	var data = scheduler._els["dhx_cal_data"][0];
	d.appendChild(data);
	d.style.cssText = "overflow:hidden; width:100%; overflow:hidden;position:relative;";
	this._obj.appendChild(d);
	
	data.style.overflowY = "hidden";
	
	var scroll = new TouchScroll(d);
	scroll.axisX = false;
	scheduler._ipad_init = function(){
		data.parentNode.style.height = data.style.height;
		data.parentNode.style.top = data.style.top;
		data.style.height = data.scrollHeight+"px";
		data.style.top = "0px";
		
		if (Math.abs(data.parentNode.offsetHeight - data.offsetHeight)<5){
			scroll.axisY=false;
			scroll.scrollTo(0,0,0);
		} else
			scroll.axisY=true;
			
		scroll.refresh();
	};

	scheduler.attachEvent("onSchedulerResize", function(){
		setTimeout(function(){
			scheduler._ipad_init();
		});
		return true;
	})
			
	scheduler._ipad_init();
};

scheduler.attachEvent("onViewChange",function(){
	scheduler._ipad_init();
});
scheduler.attachEvent("onBeforeViewChange",function(){
	scheduler._ipad_before_init();
	return true;
});

scheduler.showCover=function(box){
	this.show_cover();
	if (box){
		box.style.display="block";
		var pos = getOffset(this._obj);
		box.style.top  = box.offsetHeight*-1+"px";
		box.style.left = Math.round(pos.left+(this._obj.offsetWidth-box.offsetWidth)/2)+"px";	
	}
	
	var node =this._get_lightbox();
	node.style.webkitTransform = "translate(0px,"+(box.offsetHeight+41)+"px)";
	node.style.webkitTransitionDuration = "500ms";
};

scheduler.hideCover=function(box){
	if (box){
		box.style.webkitTransform = "translate(0px,"+(box.offsetHeight+41)*-1+"px)";
		box.style.webkitTransitionDuration = "500ms";
	}
	this.hide_cover();
}

scheduler.config.lightbox.sections[0].height = 100;
if (scheduler.form_blocks.calendar_time){
	scheduler.config.lightbox.sections[1].type = "calendar_time";
	scheduler._mini_cal_arrows = ["&lt;", "&gt;"];
}
	
scheduler.xy.menu_width = 0;
scheduler.attachEvent("onClick", function(){
	return false;
});

scheduler.locale.labels.new_event="";

scheduler._mouse_coords=function(ev){
	var pos;
	var b=document.body;
	var d = document.documentElement;
	if(ev.pageX || ev.pageY)
	    pos={x:ev.pageX, y:ev.pageY};
	else pos={
	    x:ev.clientX + (b.scrollLeft||d.scrollLeft||0) - b.clientLeft,
	    y:ev.clientY + (b.scrollTop||d.scrollTop||0) - b.clientTop
	}

	//apply layout
	pos.x-=getAbsoluteLeft(this._obj)+(this._table_view?0:this.xy.scale_width);
	var top = 
	pos.y-=getAbsoluteTop(this._obj)+this.xy.nav_height+this._dy_shift+this.xy.scale_height-(this._els["dhx_cal_data"][0]._scrollTop||0);
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
