/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.load=function(url,call){
	if (typeof call == "string"){
		this._process=call;
		var type = call;
		call = arguments[2];
	}

	this._load_url=url;
	this._after_call=call;
	if (url.$proxy) {
		url.load(this, typeof type == "string" ? type : null);
		return;
	}

	this._load(url,this._date);
};

scheduler._dp_init_backup = scheduler._dp_init;
scheduler._dp_init = function(dp) {
	dp._sendData = function(a1,rowId){
    	if (!a1) return; //nothing to send
		if (!this.callEvent("onBeforeDataSending",rowId?[rowId,this.getState(rowId),a1]:[null, null, a1])) return false;				
    	if (rowId)
			this._in_progress[rowId]=(new Date()).valueOf();
		if (this.serverProcessor.$proxy) {
			var mode = this._tMode!="POST" ? 'get' : 'post';
			var to_send = [];
			for (var i in a1)
				to_send.push({ id: i, data: a1[i], operation: this.getState(i)});
			this.serverProcessor._send(to_send, mode, this);
			return;
		}

		var a2=new dtmlXMLLoaderObject(this.afterUpdate,this,true);
		var a3 = this.serverProcessor+(this._user?(getUrlSymbol(this.serverProcessor)+["dhx_user="+this._user,"dhx_version="+this.obj.getUserData(0,"version")].join("&")):"");
		if (this._tMode!="POST")
        	a2.loadXML(a3+((a3.indexOf("?")!=-1)?"&":"?")+this.serialize(a1,rowId));
		else
        	a2.loadXML(a3,true,this.serialize(a1,rowId));
		this._waitMode++;
    };
	
	dp._updatesToParams = function(items) {
		var stack = {};
		for (var i = 0; i < items.length; i++)
			stack[items[i].id] = items[i].data;
		return this.serialize(stack);
	};

	dp._processResult = function(text, xml, loader) {
		if (loader.status != 200) {
			for (var i in this._in_progress) {
				var state = this.getState(i);
				this.afterUpdateCallback(i, i, state, null);
			}
			return;
		}
		xml = new dtmlXMLLoaderObject(function() {},this,true);
		xml.loadXMLString(text);
		xml.xmlDoc = loader;

		this.afterUpdate(this, null, null, null, xml);
	};
	this._dp_init_backup(dp);
}

if (window.dataProcessor)
	dataProcessor.prototype.init=function(obj){
		this.init_original(obj);
		obj._dataprocessor=this;
		
		this.setTransactionMode("POST",true);
		if (!this.serverProcessor.$proxy)
			this.serverProcessor+=(this.serverProcessor.indexOf("?")!=-1?"&":"?")+"editing=true";
	};