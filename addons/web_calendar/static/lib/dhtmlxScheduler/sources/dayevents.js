/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
dhx.protoUI({
	name:"dayevents",
	defaults:{
		hourFormat:"%H",
		hourClock:12,
		firstHour:0,
		lastHour:24,
		timeScaleWidth:45,
		timeScaleHeight: 30,
		scroll:true,
		scaleBorder:1,
		eventOffset:5,
		width:"auto",
		date: new Date()
	},
	$init:function(config){ 
		this.name = "DayEvents";
		
		this._dataobj.style.position = "relative";
		this.data.provideApi(this,true);
		this.data.attachEvent("onStoreUpdated",dhx.bind(this.render,this));
		
		this.attachEvent("onBeforeRender", function(){
			this._renderScale();
			this.type.color = this.config.color;
			this.type.textColor = this.config.textColor;
			this._renderobj = this._dataobj.firstChild;
			this._prepareEvents();
			if(window.scheduler)
				this.type.template = scheduler.templates.day_event;
		});
		if(window.scheduler){
			config.hourFormat = scheduler.config.scale_hour;
			config.timeScaleWidth = scheduler.xy.scale_width;
			config.timeScaleHeight = scheduler.xy.scale_height*2;
		}
	},
	_renderScale:function(){
		var html = "<div></div>";
		for(var h = this.config.firstHour; h<this.config.lastHour; h++){
			html += this.hourScaleItem(h);
		}
		this._dataobj.innerHTML = html;
	},
	_id:"dhx_l_id",
	on_click:{
	},
	hourScaleItem: function(hour){
		var isAM = (scheduler.config.hour_date.toLowerCase().indexOf("a")!=-1);
        var top = '00';
        var bottom = '30';
		if(isAM){
      	  if(hour===0)
           top = 'AM';
      	  if(hour==12)
             top = 'PM';
		  hour = (hour+11)%12+1;
		}
		if(this.config.hourFormat.indexOf("H")!=-1)
			hour = dhx.math.toFixed(hour);
        var html = "";
		var timeScaleWidth = this.config.timeScaleWidth;
		var hourHeight = this.config.timeScaleHeight;
        var sectionWidth = Math.floor(this.config.timeScaleWidth/2);
        var heightTop = Math.floor(hourHeight/2);
		var heightBottom = heightTop-this.config.scaleBorder;
		var eventZoneWidth = this._content_width-this.config.scaleBorder-this.config.timeScaleWidth;
		html += "<div style='width: 100%; height:"+hourHeight+"px;' class='dhx_dayevents_scale_item'>";
		html += "<div class='dhx_dayevents_scale_hour' style='width:"+sectionWidth+"px; height:"+hourHeight+"px;line-height:"+hourHeight+"px;'>"+hour+"</div>";
		html += "<div class='dhx_dayevents_scale_minute'  style='width:"+sectionWidth+"px'>";
		html += "<div class='dhx_dayevents_scale_top' style='width:"+sectionWidth+"px;line-height:"+heightTop+"px'>"+top+"</div>";
		html += "<div class='dhx_dayevents_scale_bottom' style='width:"+sectionWidth+"px;line-height:"+heightBottom+"px'>"+bottom+"</div>";
		html += "</div>";
		html += "<div class='dhx_dayevents_scale_event'  style='width:"+eventZoneWidth+"px'>";
		html += "<div class='dhx_dayevents_scale_top' style='height:"+heightTop+"px;width:"+eventZoneWidth+"px'></div>";
		html += "<div class='dhx_dayevents_scale_bottom' style='width: "+eventZoneWidth+"px;height:"+heightBottom+"px; '></div>";
		html += "</div>";
		html += "</div>";
        return html;		
	},
	type:{
		templateStart:dhx.Template("<div dhx_l_id='#id#' class='dhx_dayevents_event_item {common.templateCss()}' style='left:#$left#px;top:#$top#px;width:#$width#px;height:#$height#px;padding:{common.padding}px;overflow:hidden; background-color:{common.templateColor()} ;color:{common.templateTextColor()};'>"),
		template:scheduler.templates.day_event,
		templateEnd:dhx.Template("</div>"),
		templateCss:dhx.Template(""),
		templateColor:dhx.Template("#color#"),
		templateTextColor:dhx.Template("#textColor#"),
		padding:2
	},
	_prepareEvents:function(){
		var evs = this.data.getRange();
		var stack = [];
		var ev,i,j,k,_is_sorder,_max_sorder,_sorder_set;
		for(i=0; i< evs.length;i++){
			ev=evs[i];
			ev.$inner=false;
			while (stack.length && stack[stack.length-1].end_date.valueOf()<=ev.start_date.valueOf()){
				stack.splice(stack.length-1,1);
			}
			_sorder_set = false;
			
			for(j=0;j< stack.length;j++){
				if(stack[j].end_date.valueOf()<=ev.start_date.valueOf()){
					_sorder_set = true;
					ev.$sorder=stack[j].$sorder;
					stack.splice(j,1);
					ev.$inner=true;
					break;
				}
			}
			
			if (stack.length) stack[stack.length-1].$inner=true;
			
			if(!_sorder_set){
				if(stack.length){
					if(stack.length<=stack[stack.length-1].$sorder){
						if(!stack[stack.length-1].$sorder)
							ev.$sorder = 0; 
						else
							for(j=0;j<stack.length;j++){
								_is_sorder = false;
								for(k=0;k<stack.length;k++){
									if(stack[k].$sorder==j){
										_is_sorder = true;
										break;
									}
								}
								if(!_is_sorder){
									ev.$sorder = j; 
									break;
								}	
							}
						ev.$inner = true;
					}
					else{
						var _max_sorder = stack[0].$sorder;
						for(j =1;j < stack.length; j++)
							if(stack[j].$sorder>_max_sorder)
								_max_sorder = stack[j].$sorder;
						ev.$sorder = _max_sorder+1;
						ev.$inner = false;
					}
				}
				else 
					ev.$sorder = 0; 
			}
			stack.push(ev);
			if (stack.length>(stack.max_count||0)) stack.max_count=stack.length;
		}
		
		for (var i=0; i < evs.length; i++){ 
			evs[i].$count=stack.max_count;
			this._setPosition(evs[i]);
		}
	},
	_setPosition:function(ev){
		
		var date = this.config.date.getValue?this.config.date.getValue():this.config.date;
		
		var start = dhx.Date.copy(ev.start_date);
		var end = dhx.Date.copy(ev.end_date);
		var sh = start.getHours();
		var eh = end.getHours();
		if(dhx.Date.datePart(start).valueOf()>dhx.Date.datePart(end).valueOf()){
			end = start;
		}
		
		if(dhx.Date.datePart(start).valueOf()<dhx.Date.datePart(date).valueOf()){
			start = dhx.Date.datePart(date);
		}
		if(dhx.Date.datePart(end).valueOf()>dhx.Date.datePart(date).valueOf()){
			end = dhx.Date.datePart(date);
			end.setMinutes(0);
			end.setHours(this.config.lastHour);
		}
		if (sh < this.config.firstHour || eh >= this.config.lastHour){
			if (sh < this.config.firstHour){
				end.setHours(this.config.firstHour);
				ev.start_date.setMinutes(0);
			}
			if (eh >= this.config.lastHour){
				end.setMinutes(0);
				end.setHours(this.config.lastHour);
			}
		}
		var temp_width = Math.floor((this._content_width-this.config.timeScaleWidth-this.config.eventOffset-8)/ev.$count);
		ev.$left=ev.$sorder*(temp_width)+this.config.timeScaleWidth+this.config.eventOffset;
		if (!ev.$inner) temp_width=temp_width*(ev.$count-ev.$sorder);
		ev.$width = temp_width-this.config.eventOffset-this.type.padding*2;
		
		var sm = start.getHours()*60+start.getMinutes();
		var em = (end.getHours()*60+end.getMinutes())||(this.config.lastHour*60);
		ev.$top = Math.round((sm-this.config.firstHour/60)*(this.config.timeScaleHeight+1)/60); //42px/hour
		ev.$height = Math.max(10,(em-sm)*(this.config.timeScaleHeight+1)/60-2)-this.type.padding*2;
	}
}, dhx.MouseEvents, dhx.SelectionModel, dhx.Scrollable, dhx.RenderStack, dhx.DataLoader, dhx.ui.view, dhx.EventSystem, dhx.Settings);
