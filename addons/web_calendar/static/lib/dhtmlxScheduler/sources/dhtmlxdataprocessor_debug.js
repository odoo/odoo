/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
dataProcessor.prototype._o_init = dataProcessor.prototype.init;
dataProcessor.prototype.init=function(obj){
    this._console=this._console||this._createConsole();
    this.attachEvent("onValidatationError",function(rowId){
    	this._log("Validation error for ID="+(rowId||"[multiple]"));
    	return true;
	});
    return this._o_init(obj);
}

dataProcessor.prototype._createConsole=function(){
    var c=document.createElement("DIV");
    c.style.cssText='width:450px; height:420px; overflow:auto; position:absolute; z-index:99999; background-color:white; top:0px; right:0px; border:1px dashed black; font-family:Tahoma; Font-size:10pt;';
    c.innerHTML="<div style='width:100%; background-color:gray; font-weight:bold; color:white;'><span style='cursor:pointer;float:right;' onclick='this.parentNode.parentNode.style.display=\"none\"'><sup>[close]&nbsp;</sup></span><span style='cursor:pointer;float:right;' onclick='this.parentNode.parentNode.childNodes[2].innerHTML=\"\"'><sup>[clear]&nbsp;</sup></span>&nbsp;DataProcessor</div><div style='width:100%; height:200px; overflow-Y:scroll;'>&nbsp;Current state</div><div style='width:100%; height:200px; overflow-Y:scroll;'>&nbsp;Log:</div>";
    if (document.body) document.body.insertBefore(c,document.body.firstChild);
    else dhtmlxEvent(window,"load",function(){
        document.body.insertBefore(c,document.body.firstChild);
    })    
    dhtmlxEvent(window,"dblclick",function(){ 
        c.style.display='';
    })    
    return c;
}

dataProcessor.prototype._error=function(data){
	this._log("<span style='color:red'>"+data+"</span>");
}
dataProcessor.prototype._log=function(data){
	var div=document.createElement("DIV");
	div.innerHTML = data;
	var parent=this._console.childNodes[2];
    parent.appendChild(div);
    parent.scrollTop=parent.scrollHeight;
    
    if (window.console && window.console.log)
    	window.console.log("DataProcessor :: "+data.replace("&nbsp;"," ").replace("<b>","").replace("</b>",""));
    
}
dataProcessor.prototype._updateStat=function(data){
    var data=["&nbsp;Current state"];
    for(var i=0;i<this.updatedRows.length;i++)
	    data.push("&nbsp;ID:"+this.updatedRows[i]+" Status: "+(this.obj.getUserData(this.updatedRows[i],"!nativeeditor_status")||"updated")+", "+(this.is_invalid(this.updatedRows[i])||"valid"))
	this._console.childNodes[1].innerHTML=data.join("<br/>")+"<hr/>Current mode: "+this.updateMode;
}
dataProcessor.prototype.xml_analize=function(xml){
	if (_isFF){
		if (!xml.xmlDoc.responseXML)
			this._error("Not an XML, probably incorrect content type specified ( must be text/xml ), or some text output was started before XML data");
		else if (xml.xmlDoc.responseXML.firstChild.tagName=="parsererror")
			this._error(xml.xmlDoc.responseXML.firstChild.textContent);
		else return true;
	} else if (_isIE){
		if (xml.xmlDoc.responseXML.parseError.errorCode)
			this._error("XML error : "+xml.xmlDoc.responseXML.parseError.reason);
		else if (!xml.xmlDoc.responseXML.documentElement) 
			this._error("Not an XML, probably incorrect content type specified ( must be text/xml ), or some text output was started before XML data");
		else return true;
	}
	return false;
}

dataProcessor.wrap=function(name,before,after){
	var d=dataProcessor.prototype;
	if (!d._wrap) d._wrap={};
	d._wrap[name]=d[name];
	d[name]=function(){
		if (before) before.apply(this,arguments);
		var res=d._wrap[name].apply(this,arguments);
		if (after) after.apply(this,[arguments,res]);
		return res;
	}
};

dataProcessor.wrap("setUpdated",function(rowId,state,mode){
	this._log("&nbsp;row <b>"+rowId+"</b> "+(state?"marked":"unmarked")+" ["+(mode||"updated")+","+(this.is_invalid(rowId)||"valid")+"]");
},function(){
	this._updateStat();
});



dataProcessor.wrap("sendData",function(rowId){
	if (rowId){
		this._log("&nbsp;Initiating data sending for <b>"+rowId+"</b>");
		if (this.obj.mytype=="tree"){
        	if (!this.obj._idpull[rowId])
	    		this._log("&nbsp;Error! item with such ID not exists <b>"+rowId+"</b>");
		} else {
			if (this.rowsAr && !this.obj.rowsAr[rowId])
	        	this._log("&nbsp;Error! row with such ID not exists <b>"+rowId+"</b>");
        }
	}
},function(){
	
});

dataProcessor.wrap("sendAllData",function(){
	this._log("&nbsp;Initiating data sending for <b>all</b> rows ");
},function(){
	
});
dataProcessor.logSingle=function(data,id){
	var tdata = {};
	if (id)
		tdata[id] = data;
	else
		tdata = data;
		
	var url = [];
	for (var key in tdata) {
		url.push("<fieldset><legend>"+key+"</legend>");
		var suburl = [];
		
		for (var ikey in tdata[key])
			suburl.push(ikey+" = "+tdata[key][ikey]);

		url.push(suburl.join("<br>"));
		url.push("</fieldset>");
	}
	return url.join("");
}
dataProcessor.wrap("_sendData",function(data,rowId){
	if (rowId)
		this._log("&nbsp;Sending in one-by-one mode, current ID = "+rowId);
	else
		this._log("&nbsp;Sending all data at once");
	this._log("&nbsp;Server url: "+this.serverProcessor+" <a onclick='this.parentNode.nextSibling.firstChild.style.display=\"block\"' href='#'>parameters</a>");
	var url = [];
	this._log("<blockquote style='display:none;'>"+dataProcessor.logSingle(data,rowId)+"<blockquote>");
},function(){
	
});


dataProcessor.wrap("afterUpdate",function(that,b,c,d,xml){
	that._log("&nbsp;Server response received <a onclick='this.nextSibling.style.display=\"block\"' href='#'>details</a><blockquote style='display:none'><code>"+(xml.xmlDoc.responseText||"").replace(/\&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")+"</code></blockquote>");			
	if (!that.xml_analize(xml)) return;
	var atag=xml.doXPath("//data/action");
	if (!atag){
		that._log("&nbsp;No actions found");
		var atag=xml.getXMLTopNode("data");
		if (!atag) that._log("&nbsp;XML not valid");
		else that._log("&nbsp;Incorrect content type - need to be text/xml"); 
	}
},function(){
	
});

dataProcessor.wrap("afterUpdateCallback",function(sid,tid,action){
	if (this.obj.mytype=="tree"){
		if (!this.obj._idpull[sid]) this._log("Incorrect SID, item with such ID not exists in grid");
	} else {
		if (this.obj.rowsAr && !this.obj.rowsAr[sid]) this._log("Incorrect SID, row with such ID not exists in grid");
	}
	this._log("&nbsp;Action: "+action+" SID:"+sid+" TID:"+tid);
},function(){
	
});






