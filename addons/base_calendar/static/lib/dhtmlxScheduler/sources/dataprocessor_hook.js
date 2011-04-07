scheduler._dp_init=function(dp){
	dp._methods=["setEventTextStyle","","changeEventId","deleteEvent"];
	
	this.attachEvent("onEventAdded",function(id){
		if (!this._loading && this.validId(id))
			dp.setUpdated(id,true,"inserted");
	});
	this.attachEvent("onBeforeEventDelete",function(id){
		if (!this.validId(id)) return;
        var z=dp.getState(id);
        
		if (z=="inserted" || this._new_event) {  dp.setUpdated(id,false);		return true; }
		if (z=="deleted")  return false;
    	if (z=="true_deleted")  return true;
    	
		dp.setUpdated(id,true,"deleted");
      	return false;
	});
	this.attachEvent("onEventChanged",function(id){
		if (!this._loading && this.validId(id))
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


scheduler.setUserData=function(id,name,value){
	if (id)
		this.getEvent(id)[name]=value;
	else
		this._userdata[name]=value;
};
scheduler.getUserData=function(id,name){
	return id?this.getEvent(id)[name]:this._userdata[name];
};
scheduler.setEventTextStyle=function(id,style){
	this.for_rendered(id,function(r){
		r.style.cssText+=";"+style;
	});
	var ev = this.getEvent(id);
	ev["_text_style"]=style;
	this.event_updated(ev);
};
scheduler.validId=function(id){
	return true;
};

scheduler._update_callback = function(upd,id){
	var data		=	scheduler.xmlNodeToJSON(upd.firstChild);
	data.text		=	data.text||data._tagvalue;
	data.start_date	=	scheduler.templates.xml_date(data.start_date);
	data.end_date	=	scheduler.templates.xml_date(data.end_date);
	
	scheduler.addEvent(data);
};