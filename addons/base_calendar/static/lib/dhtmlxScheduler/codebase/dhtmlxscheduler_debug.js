/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/

dhtmlx=function(obj){
	for (var a in obj) dhtmlx[a]=obj[a];
	return dhtmlx; //simple singleton
};
dhtmlx.extend_api=function(name,map,ext){
	var t = window[name];
	if (!t) return; //component not defined
	window[name]=function(obj){
		if (obj && typeof obj == "object" && !obj.tagName && !(obj instanceof Array)){
			var that = t.apply(this,(map._init?map._init(obj):arguments));
			//global settings
			for (var a in dhtmlx)
				if (map[a]) this[map[a]](dhtmlx[a]);			
			//local settings
			for (var a in obj){
				if (map[a]) this[map[a]](obj[a]);
				else if (a.indexOf("on")==0){
					this.attachEvent(a,obj[a]);
				}
			}
		} else
			var that = t.apply(this,arguments);
		if (map._patch) map._patch(this);
		return that||this;
	};
	window[name].prototype=t.prototype;
	if (ext)
		dhtmlXHeir(window[name].prototype,ext);
};

dhtmlxAjax={
	get:function(url,callback){
		var t=new dtmlXMLLoaderObject(true);
		t.async=(arguments.length<3);
		t.waitCall=callback;
		t.loadXML(url)
		return t;
	},
	post:function(url,post,callback){
		var t=new dtmlXMLLoaderObject(true);
		t.async=(arguments.length<4);
		t.waitCall=callback;
		t.loadXML(url,true,post)
		return t;
	},
	getSync:function(url){
		return this.get(url,null,true)
	},
	postSync:function(url,post){
		return this.post(url,post,null,true);		
	}
}

/**
  *     @desc: xmlLoader object
  *     @type: private
  *     @param: funcObject - xml parser function
  *     @param: object - jsControl object
  *     @param: async - sync/async mode (async by default)
  *     @param: rSeed - enable/disable random seed ( prevent IE caching)
  *     @topic: 0
  */
function dtmlXMLLoaderObject(funcObject, dhtmlObject, async, rSeed){
	this.xmlDoc="";

	if (typeof (async) != "undefined")
		this.async=async;
	else
		this.async=true;

	this.onloadAction=funcObject||null;
	this.mainObject=dhtmlObject||null;
	this.waitCall=null;
	this.rSeed=rSeed||false;
	return this;
};
/**
  *     @desc: xml loading handler
  *     @type: private
  *     @param: dtmlObject - xmlLoader object
  *     @topic: 0
  */
dtmlXMLLoaderObject.prototype.waitLoadFunction=function(dhtmlObject){
	var once = true;
	this.check=function (){
		if ((dhtmlObject)&&(dhtmlObject.onloadAction != null)){
			if ((!dhtmlObject.xmlDoc.readyState)||(dhtmlObject.xmlDoc.readyState == 4)){
				if (!once)
					return;

				once=false; //IE 5 fix
				if (typeof dhtmlObject.onloadAction == "function")
					dhtmlObject.onloadAction(dhtmlObject.mainObject, null, null, null, dhtmlObject);

				if (dhtmlObject.waitCall){
					dhtmlObject.waitCall.call(this,dhtmlObject);
					dhtmlObject.waitCall=null;
				}
			}
		}
	};
	return this.check;
};

/**
  *     @desc: return XML top node
  *     @param: tagName - top XML node tag name (not used in IE, required for Safari and Mozilla)
  *     @type: private
  *     @returns: top XML node
  *     @topic: 0  
  */
dtmlXMLLoaderObject.prototype.getXMLTopNode=function(tagName, oldObj){
	if (this.xmlDoc.responseXML){
		var temp = this.xmlDoc.responseXML.getElementsByTagName(tagName);
		if(temp.length==0 && tagName.indexOf(":")!=-1)
			var temp = this.xmlDoc.responseXML.getElementsByTagName((tagName.split(":"))[1]);
		var z = temp[0];
	} else
		var z = this.xmlDoc.documentElement;

	if (z){
		this._retry=false;
		return z;
	}

	if ((_isIE)&&(!this._retry)){
		//fall back to MS.XMLDOM
		var xmlString = this.xmlDoc.responseText;
		var oldObj = this.xmlDoc;
		this._retry=true;
		this.xmlDoc=new ActiveXObject("Microsoft.XMLDOM");
		this.xmlDoc.async=false;
		this.xmlDoc["loadXM"+"L"](xmlString);

		return this.getXMLTopNode(tagName, oldObj);
	}
	dhtmlxError.throwError("LoadXML", "Incorrect XML", [
		(oldObj||this.xmlDoc),
		this.mainObject
	]);

	return document.createElement("DIV");
};

/**
  *     @desc: load XML from string
  *     @type: private
  *     @param: xmlString - xml string
  *     @topic: 0  
  */
dtmlXMLLoaderObject.prototype.loadXMLString=function(xmlString){
	{
		try{
			var parser = new DOMParser();
			this.xmlDoc=parser.parseFromString(xmlString, "text/xml");
		}
		catch (e){
			this.xmlDoc=new ActiveXObject("Microsoft.XMLDOM");
			this.xmlDoc.async=this.async;
			this.xmlDoc["loadXM"+"L"](xmlString);
		}
	}

	this.onloadAction(this.mainObject, null, null, null, this);

	if (this.waitCall){
		this.waitCall();
		this.waitCall=null;
	}
}
/**
  *     @desc: load XML
  *     @type: private
  *     @param: filePath - xml file path
  *     @param: postMode - send POST request
  *     @param: postVars - list of vars for post request
  *     @topic: 0
  */
dtmlXMLLoaderObject.prototype.loadXML=function(filePath, postMode, postVars, rpc){
	if (this.rSeed)
		filePath+=((filePath.indexOf("?") != -1) ? "&" : "?")+"a_dhx_rSeed="+(new Date()).valueOf();
	this.filePath=filePath;
	if ((!_isIE)&&(window.XMLHttpRequest))
		this.xmlDoc=new XMLHttpRequest();
	else {
		this.xmlDoc=new ActiveXObject("Microsoft.XMLHTTP");
	}

	if (this.async)
		this.xmlDoc.onreadystatechange=new this.waitLoadFunction(this);
	this.xmlDoc.open(postMode ? "POST" : "GET", filePath, this.async);

	if (rpc){
		this.xmlDoc.setRequestHeader("User-Agent", "dhtmlxRPC v0.1 ("+navigator.userAgent+")");
		this.xmlDoc.setRequestHeader("Content-type", "text/xml");
	}

	else if (postMode)
		this.xmlDoc.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
		
	this.xmlDoc.setRequestHeader("X-Requested-With","XMLHttpRequest");
	this.xmlDoc.send(null||postVars);

	if (!this.async)
		(new this.waitLoadFunction(this))();
};
/**
  *     @desc: destructor, cleans used memory
  *     @type: private
  *     @topic: 0
  */
dtmlXMLLoaderObject.prototype.destructor=function(){
	this.onloadAction=null;
	this.mainObject=null;
	this.xmlDoc=null;
	return null;
}

dtmlXMLLoaderObject.prototype.xmlNodeToJSON = function(node){
        var t={};
        for (var i=0; i<node.attributes.length; i++)
            t[node.attributes[i].name]=node.attributes[i].value;
        t["_tagvalue"]=node.firstChild?node.firstChild.nodeValue:"";
        for (var i=0; i<node.childNodes.length; i++){
            var name=node.childNodes[i].tagName;
            if (name){
                if (!t[name]) t[name]=[];
                t[name].push(this.xmlNodeToJSON(node.childNodes[i]));
            }            
        }        
        return t;
    }

/**  
  *     @desc: Call wrapper
  *     @type: private
  *     @param: funcObject - action handler
  *     @param: dhtmlObject - user data
  *     @returns: function handler
  *     @topic: 0  
  */
function callerFunction(funcObject, dhtmlObject){
	this.handler=function(e){
		if (!e)
			e=window.event;
		funcObject(e, dhtmlObject);
		return true;
	};
	return this.handler;
};

/**  
  *     @desc: Calculate absolute position of html object
  *     @type: private
  *     @param: htmlObject - html object
  *     @topic: 0  
  */
function getAbsoluteLeft(htmlObject){
	return getOffset(htmlObject).left;
}
/**
  *     @desc: Calculate absolute position of html object
  *     @type: private
  *     @param: htmlObject - html object
  *     @topic: 0  
  */
function getAbsoluteTop(htmlObject){
	return getOffset(htmlObject).top;
}

function getOffsetSum(elem) {
	var top=0, left=0;
	while(elem) {
		top = top + parseInt(elem.offsetTop);
		left = left + parseInt(elem.offsetLeft);
		elem = elem.offsetParent;
	}
	return {top: top, left: left};
}
function getOffsetRect(elem) {
	var box = elem.getBoundingClientRect();
	var body = document.body;
	var docElem = document.documentElement;
	var scrollTop = window.pageYOffset || docElem.scrollTop || body.scrollTop;
	var scrollLeft = window.pageXOffset || docElem.scrollLeft || body.scrollLeft;
	var clientTop = docElem.clientTop || body.clientTop || 0;
	var clientLeft = docElem.clientLeft || body.clientLeft || 0;
	var top  = box.top +  scrollTop - clientTop;
	var left = box.left + scrollLeft - clientLeft;
	return { top: Math.round(top), left: Math.round(left) };
}
function getOffset(elem) {
	if (elem.getBoundingClientRect && !_isChrome) {
		return getOffsetRect(elem);
	} else {
		return getOffsetSum(elem);
	}
}

/**  
*     @desc: Convert string to it boolean representation
*     @type: private
*     @param: inputString - string for covertion
*     @topic: 0
*/
function convertStringToBoolean(inputString){
	if (typeof (inputString) == "string")
		inputString=inputString.toLowerCase();

	switch (inputString){
		case "1":
		case "true":
		case "yes":
		case "y":
		case 1:
		case true:
			return true;
			break;

		default: return false;
	}
}

/**  
*     @desc: find out what symbol to use as url param delimiters in further params
*     @type: private
*     @param: str - current url string
*     @topic: 0  
*/
function getUrlSymbol(str){
	if (str.indexOf("?") != -1)
		return "&"
	else
		return "?"
}

function dhtmlDragAndDropObject(){
	if (window.dhtmlDragAndDrop)
		return window.dhtmlDragAndDrop;

	this.lastLanding=0;
	this.dragNode=0;
	this.dragStartNode=0;
	this.dragStartObject=0;
	this.tempDOMU=null;
	this.tempDOMM=null;
	this.waitDrag=0;
	window.dhtmlDragAndDrop=this;

	return this;
};

dhtmlDragAndDropObject.prototype.removeDraggableItem=function(htmlNode){
	htmlNode.onmousedown=null;
	htmlNode.dragStarter=null;
	htmlNode.dragLanding=null;
}
dhtmlDragAndDropObject.prototype.addDraggableItem=function(htmlNode, dhtmlObject){
	htmlNode.onmousedown=this.preCreateDragCopy;
	htmlNode.dragStarter=dhtmlObject;
	this.addDragLanding(htmlNode, dhtmlObject);
}
dhtmlDragAndDropObject.prototype.addDragLanding=function(htmlNode, dhtmlObject){
	htmlNode.dragLanding=dhtmlObject;
}
dhtmlDragAndDropObject.prototype.preCreateDragCopy=function(e){
	if ((e||event) && (e||event).button == 2)
		return;

	if (window.dhtmlDragAndDrop.waitDrag){
		window.dhtmlDragAndDrop.waitDrag=0;
		document.body.onmouseup=window.dhtmlDragAndDrop.tempDOMU;
		document.body.onmousemove=window.dhtmlDragAndDrop.tempDOMM;
		return false;
	}

	window.dhtmlDragAndDrop.waitDrag=1;
	window.dhtmlDragAndDrop.tempDOMU=document.body.onmouseup;
	window.dhtmlDragAndDrop.tempDOMM=document.body.onmousemove;
	window.dhtmlDragAndDrop.dragStartNode=this;
	window.dhtmlDragAndDrop.dragStartObject=this.dragStarter;
	document.body.onmouseup=window.dhtmlDragAndDrop.preCreateDragCopy;
	document.body.onmousemove=window.dhtmlDragAndDrop.callDrag;
	window.dhtmlDragAndDrop.downtime = new Date().valueOf();
	

	if ((e)&&(e.preventDefault)){
		e.preventDefault();
		return false;
	}
	return false;
};
dhtmlDragAndDropObject.prototype.callDrag=function(e){
	if (!e)
		e=window.event;
	dragger=window.dhtmlDragAndDrop;
	if ((new Date()).valueOf()-dragger.downtime<100) return;

	if ((e.button == 0)&&(_isIE))
		return dragger.stopDrag();

	if (!dragger.dragNode&&dragger.waitDrag){
		dragger.dragNode=dragger.dragStartObject._createDragNode(dragger.dragStartNode, e);

		if (!dragger.dragNode)
			return dragger.stopDrag();

		dragger.dragNode.onselectstart=function(){return false;}
		dragger.gldragNode=dragger.dragNode;
		document.body.appendChild(dragger.dragNode);
		document.body.onmouseup=dragger.stopDrag;
		dragger.waitDrag=0;
		dragger.dragNode.pWindow=window;
		dragger.initFrameRoute();
	}

	if (dragger.dragNode.parentNode != window.document.body){
		var grd = dragger.gldragNode;

		if (dragger.gldragNode.old)
			grd=dragger.gldragNode.old;

		//if (!document.all) dragger.calculateFramePosition();
		grd.parentNode.removeChild(grd);
		var oldBody = dragger.dragNode.pWindow;

		//		var oldp=dragger.dragNode.parentObject;
		if (_isIE){
			var div = document.createElement("Div");
			div.innerHTML=dragger.dragNode.outerHTML;
			dragger.dragNode=div.childNodes[0];
		} else
			dragger.dragNode=dragger.dragNode.cloneNode(true);

		dragger.dragNode.pWindow=window;
		//		dragger.dragNode.parentObject=oldp;

		dragger.gldragNode.old=dragger.dragNode;
		document.body.appendChild(dragger.dragNode);
		oldBody.dhtmlDragAndDrop.dragNode=dragger.dragNode;
	}

	dragger.dragNode.style.left=e.clientX+15+(dragger.fx
		? dragger.fx*(-1)
		: 0)
		+(document.body.scrollLeft||document.documentElement.scrollLeft)+"px";
	dragger.dragNode.style.top=e.clientY+3+(dragger.fy
		? dragger.fy*(-1)
		: 0)
		+(document.body.scrollTop||document.documentElement.scrollTop)+"px";

	if (!e.srcElement)
		var z = e.target;
	else
		z=e.srcElement;
	dragger.checkLanding(z, e);
}

dhtmlDragAndDropObject.prototype.calculateFramePosition=function(n){
	//this.fx = 0, this.fy = 0;
	if (window.name){
		var el = parent.frames[window.name].frameElement.offsetParent;
		var fx = 0;
		var fy = 0;

		while (el){
			fx+=el.offsetLeft;
			fy+=el.offsetTop;
			el=el.offsetParent;
		}

		if ((parent.dhtmlDragAndDrop)){
			var ls = parent.dhtmlDragAndDrop.calculateFramePosition(1);
			fx+=ls.split('_')[0]*1;
			fy+=ls.split('_')[1]*1;
		}

		if (n)
			return fx+"_"+fy;
		else
			this.fx=fx;
		this.fy=fy;
	}
	return "0_0";
}
dhtmlDragAndDropObject.prototype.checkLanding=function(htmlObject, e){
	if ((htmlObject)&&(htmlObject.dragLanding)){
		if (this.lastLanding)
			this.lastLanding.dragLanding._dragOut(this.lastLanding);
		this.lastLanding=htmlObject;
		this.lastLanding=this.lastLanding.dragLanding._dragIn(this.lastLanding, this.dragStartNode, e.clientX,
			e.clientY, e);
		this.lastLanding_scr=(_isIE ? e.srcElement : e.target);
	} else {
		if ((htmlObject)&&(htmlObject.tagName != "BODY"))
			this.checkLanding(htmlObject.parentNode, e);
		else {
			if (this.lastLanding)
				this.lastLanding.dragLanding._dragOut(this.lastLanding, e.clientX, e.clientY, e);
			this.lastLanding=0;

			if (this._onNotFound)
				this._onNotFound();
		}
	}
}
dhtmlDragAndDropObject.prototype.stopDrag=function(e, mode){
	dragger=window.dhtmlDragAndDrop;

	if (!mode){
		dragger.stopFrameRoute();
		var temp = dragger.lastLanding;
		dragger.lastLanding=null;

		if (temp)
			temp.dragLanding._drag(dragger.dragStartNode, dragger.dragStartObject, temp, (_isIE
				? event.srcElement
				: e.target));
	}
	dragger.lastLanding=null;

	if ((dragger.dragNode)&&(dragger.dragNode.parentNode == document.body))
		dragger.dragNode.parentNode.removeChild(dragger.dragNode);
	dragger.dragNode=0;
	dragger.gldragNode=0;
	dragger.fx=0;
	dragger.fy=0;
	dragger.dragStartNode=0;
	dragger.dragStartObject=0;
	document.body.onmouseup=dragger.tempDOMU;
	document.body.onmousemove=dragger.tempDOMM;
	dragger.tempDOMU=null;
	dragger.tempDOMM=null;
	dragger.waitDrag=0;
}

dhtmlDragAndDropObject.prototype.stopFrameRoute=function(win){
	if (win)
		window.dhtmlDragAndDrop.stopDrag(1, 1);

	for (var i = 0; i < window.frames.length; i++){
		try{
		if ((window.frames[i] != win)&&(window.frames[i].dhtmlDragAndDrop))
			window.frames[i].dhtmlDragAndDrop.stopFrameRoute(window);
		} catch(e){}
	}

	try{
	if ((parent.dhtmlDragAndDrop)&&(parent != window)&&(parent != win))
		parent.dhtmlDragAndDrop.stopFrameRoute(window);
	} catch(e){}
}
dhtmlDragAndDropObject.prototype.initFrameRoute=function(win, mode){
	if (win){
		window.dhtmlDragAndDrop.preCreateDragCopy({});
		window.dhtmlDragAndDrop.dragStartNode=win.dhtmlDragAndDrop.dragStartNode;
		window.dhtmlDragAndDrop.dragStartObject=win.dhtmlDragAndDrop.dragStartObject;
		window.dhtmlDragAndDrop.dragNode=win.dhtmlDragAndDrop.dragNode;
		window.dhtmlDragAndDrop.gldragNode=win.dhtmlDragAndDrop.dragNode;
		window.document.body.onmouseup=window.dhtmlDragAndDrop.stopDrag;
		window.waitDrag=0;

		if (((!_isIE)&&(mode))&&((!_isFF)||(_FFrv < 1.8)))
			window.dhtmlDragAndDrop.calculateFramePosition();
	}
	try{
	if ((parent.dhtmlDragAndDrop)&&(parent != window)&&(parent != win))
		parent.dhtmlDragAndDrop.initFrameRoute(window);
	}catch(e){}

	for (var i = 0; i < window.frames.length; i++){
		try{
		if ((window.frames[i] != win)&&(window.frames[i].dhtmlDragAndDrop))
			window.frames[i].dhtmlDragAndDrop.initFrameRoute(window, ((!win||mode) ? 1 : 0));
		} catch(e){}
	}
}

var _isFF = false;
var _isIE = false;
var _isOpera = false;
var _isKHTML = false;
var _isMacOS = false;
var _isChrome = false;

if (navigator.userAgent.indexOf('Macintosh') != -1)
	_isMacOS=true;


if (navigator.userAgent.toLowerCase().indexOf('chrome')>-1)
	_isChrome=true;

if ((navigator.userAgent.indexOf('Safari') != -1)||(navigator.userAgent.indexOf('Konqueror') != -1)){
	var _KHTMLrv = parseFloat(navigator.userAgent.substr(navigator.userAgent.indexOf('Safari')+7, 5));

	if (_KHTMLrv > 525){ //mimic FF behavior for Safari 3.1+
		_isFF=true;
		var _FFrv = 1.9;
	} else
		_isKHTML=true;
} else if (navigator.userAgent.indexOf('Opera') != -1){
	_isOpera=true;
	_OperaRv=parseFloat(navigator.userAgent.substr(navigator.userAgent.indexOf('Opera')+6, 3));
}


else if (navigator.appName.indexOf("Microsoft") != -1){
	_isIE=true;
	if (navigator.appVersion.indexOf("MSIE 8.0")!= -1 && document.compatMode != "BackCompat") _isIE=8;
} else {
	_isFF=true;
	var _FFrv = parseFloat(navigator.userAgent.split("rv:")[1])
}


//multibrowser Xpath processor
dtmlXMLLoaderObject.prototype.doXPath=function(xpathExp, docObj, namespace, result_type){
	if (_isKHTML || (!_isIE && !window.XPathResult))
		return this.doXPathOpera(xpathExp, docObj);

	if (_isIE){ //IE
		if (!docObj)
			if (!this.xmlDoc.nodeName)
				docObj=this.xmlDoc.responseXML
			else
				docObj=this.xmlDoc;

		if (!docObj)
			dhtmlxError.throwError("LoadXML", "Incorrect XML", [
				(docObj||this.xmlDoc),
				this.mainObject
			]);

		if (namespace != null)
			docObj.setProperty("SelectionNamespaces", "xmlns:xsl='"+namespace+"'"); //

		if (result_type == 'single'){
			return docObj.selectSingleNode(xpathExp);
		}
		else {
			return docObj.selectNodes(xpathExp)||new Array(0);
		}
	} else { //Mozilla
		var nodeObj = docObj;

		if (!docObj){
			if (!this.xmlDoc.nodeName){
				docObj=this.xmlDoc.responseXML
			}
			else {
				docObj=this.xmlDoc;
			}
		}

		if (!docObj)
			dhtmlxError.throwError("LoadXML", "Incorrect XML", [
				(docObj||this.xmlDoc),
				this.mainObject
			]);

		if (docObj.nodeName.indexOf("document") != -1){
			nodeObj=docObj;
		}
		else {
			nodeObj=docObj;
			docObj=docObj.ownerDocument;
		}
		var retType = XPathResult.ANY_TYPE;

		if (result_type == 'single')
			retType=XPathResult.FIRST_ORDERED_NODE_TYPE
		var rowsCol = new Array();
		var col = docObj.evaluate(xpathExp, nodeObj, function(pref){
			return namespace
		}, retType, null);

		if (retType == XPathResult.FIRST_ORDERED_NODE_TYPE){
			return col.singleNodeValue;
		}
		var thisColMemb = col.iterateNext();

		while (thisColMemb){
			rowsCol[rowsCol.length]=thisColMemb;
			thisColMemb=col.iterateNext();
		}
		return rowsCol;
	}
}

function _dhtmlxError(type, name, params){
	if (!this.catches)
		this.catches=new Array();

	return this;
}

_dhtmlxError.prototype.catchError=function(type, func_name){
	this.catches[type]=func_name;
}
_dhtmlxError.prototype.throwError=function(type, name, params){
	if (this.catches[type])
		return this.catches[type](type, name, params);

	if (this.catches["ALL"])
		return this.catches["ALL"](type, name, params);

	alert("Error type: "+arguments[0]+"\nDescription: "+arguments[1]);
	return null;
}

window.dhtmlxError=new _dhtmlxError();


//opera fake, while 9.0 not released
//multibrowser Xpath processor
dtmlXMLLoaderObject.prototype.doXPathOpera=function(xpathExp, docObj){
	//this is fake for Opera
	var z = xpathExp.replace(/[\/]+/gi, "/").split('/');
	var obj = null;
	var i = 1;

	if (!z.length)
		return [];

	if (z[0] == ".")
		obj=[docObj]; else if (z[0] == ""){
		obj=(this.xmlDoc.responseXML||this.xmlDoc).getElementsByTagName(z[i].replace(/\[[^\]]*\]/g, ""));
		i++;
	} else
		return [];

	for (i; i < z.length; i++)obj=this._getAllNamedChilds(obj, z[i]);

	if (z[i-1].indexOf("[") != -1)
		obj=this._filterXPath(obj, z[i-1]);
	return obj;
}

dtmlXMLLoaderObject.prototype._filterXPath=function(a, b){
	var c = new Array();
	var b = b.replace(/[^\[]*\[\@/g, "").replace(/[\[\]\@]*/g, "");

	for (var i = 0; i < a.length; i++)
		if (a[i].getAttribute(b))
			c[c.length]=a[i];

	return c;
}
dtmlXMLLoaderObject.prototype._getAllNamedChilds=function(a, b){
	var c = new Array();

	if (_isKHTML)
		b=b.toUpperCase();

	for (var i = 0; i < a.length; i++)for (var j = 0; j < a[i].childNodes.length; j++){
		if (_isKHTML){
			if (a[i].childNodes[j].tagName&&a[i].childNodes[j].tagName.toUpperCase() == b)
				c[c.length]=a[i].childNodes[j];
		}

		else if (a[i].childNodes[j].tagName == b)
			c[c.length]=a[i].childNodes[j];
	}

	return c;
}

function dhtmlXHeir(a, b){
	for (var c in b)
		if (typeof (b[c]) == "function")
			a[c]=b[c];
	return a;
}

function dhtmlxEvent(el, event, handler){
	if (el.addEventListener)
		el.addEventListener(event, handler, false);

	else if (el.attachEvent)
		el.attachEvent("on"+event, handler);
}

//============= XSL Extension ===================================

dtmlXMLLoaderObject.prototype.xslDoc=null;
dtmlXMLLoaderObject.prototype.setXSLParamValue=function(paramName, paramValue, xslDoc){
	if (!xslDoc)
		xslDoc=this.xslDoc

	if (xslDoc.responseXML)
		xslDoc=xslDoc.responseXML;
	var item =
		this.doXPath("/xsl:stylesheet/xsl:variable[@name='"+paramName+"']", xslDoc,
			"http:/\/www.w3.org/1999/XSL/Transform", "single");

	if (item != null)
		item.firstChild.nodeValue=paramValue
}
dtmlXMLLoaderObject.prototype.doXSLTransToObject=function(xslDoc, xmlDoc){
	if (!xslDoc)
		xslDoc=this.xslDoc;

	if (xslDoc.responseXML)
		xslDoc=xslDoc.responseXML

	if (!xmlDoc)
		xmlDoc=this.xmlDoc;

	if (xmlDoc.responseXML)
		xmlDoc=xmlDoc.responseXML

	//MOzilla
	if (!_isIE){
		if (!this.XSLProcessor){
			this.XSLProcessor=new XSLTProcessor();
			this.XSLProcessor.importStylesheet(xslDoc);
		}
		var result = this.XSLProcessor.transformToDocument(xmlDoc);
	} else {
		var result = new ActiveXObject("Msxml2.DOMDocument.3.0");
		try{
			xmlDoc.transformNodeToObject(xslDoc, result);
		}catch(e){
			result = xmlDoc.transformNode(xslDoc);
		}
	}
	return result;
}

dtmlXMLLoaderObject.prototype.doXSLTransToString=function(xslDoc, xmlDoc){
	var res = this.doXSLTransToObject(xslDoc, xmlDoc);
	if(typeof(res)=="string")
		return res;
	return this.doSerialization(res);
}

dtmlXMLLoaderObject.prototype.doSerialization=function(xmlDoc){
	if (!xmlDoc)
			xmlDoc=this.xmlDoc;
	if (xmlDoc.responseXML)
			xmlDoc=xmlDoc.responseXML
	if (!_isIE){
		var xmlSerializer = new XMLSerializer();
		return xmlSerializer.serializeToString(xmlDoc);
	} else
		return xmlDoc.xml;
}

/**
*   @desc: 
*   @type: private
*/
dhtmlxEventable=function(obj){
		obj.dhx_SeverCatcherPath="";
		obj.attachEvent=function(name, catcher, callObj){
			name='ev_'+name.toLowerCase();
			if (!this[name])
				this[name]=new this.eventCatcher(callObj||this);
				
			return(name+':'+this[name].addEvent(catcher)); //return ID (event name & event ID)
		}
		obj.callEvent=function(name, arg0){ 
			name='ev_'+name.toLowerCase();
			if (this[name])
				return this[name].apply(this, arg0);
			return true;
		}
		obj.checkEvent=function(name){
			return (!!this['ev_'+name.toLowerCase()])
		}
		obj.eventCatcher=function(obj){
			var dhx_catch = [];
			var z = function(){
				var res = true;
				for (var i = 0; i < dhx_catch.length; i++){
					if (dhx_catch[i] != null){
						var zr = dhx_catch[i].apply(obj, arguments);
						res=res&&zr;
					}
				}
				return res;
			}
			z.addEvent=function(ev){
				if (typeof (ev) != "function")
					ev=eval(ev);
				if (ev)
					return dhx_catch.push(ev)-1;
				return false;
			}
			z.removeEvent=function(id){
				dhx_catch[id]=null;
			}
			return z;
		}
		obj.detachEvent=function(id){
			if (id != false){
				var list = id.split(':');           //get EventName and ID
				this[list[0]].removeEvent(list[1]); //remove event
			}
		}
}

/**
	* 	@desc: constructor, data processor object 
	*	@param: serverProcessorURL - url used for update
	*	@type: public
	*/
function dataProcessor(serverProcessorURL){
    this.serverProcessor = serverProcessorURL;
    this.action_param="!nativeeditor_status";
    
	this.object = null;
	this.updatedRows = []; //ids of updated rows
	
	this.autoUpdate = true;
	this.updateMode = "cell";
	this._tMode="GET"; 
	this.post_delim = "_";
	
    this._waitMode=0;
    this._in_progress={};//?
    this._invalid={};
    this.mandatoryFields=[];
    this.messages=[];
    
    this.styles={
    	updated:"font-weight:bold;",
    	inserted:"font-weight:bold;",
    	deleted:"text-decoration : line-through;",
    	invalid:"background-color:FFE0E0;",
    	invalid_cell:"border-bottom:2px solid red;",
    	error:"color:red;",
    	clear:"font-weight:normal;text-decoration:none;"
    };
    
    this.enableUTFencoding(true);
    dhtmlxEventable(this);

    return this;
    }

dataProcessor.prototype={
	/**
	* 	@desc: select GET or POST transaction model
	*	@param: mode - GET/POST
	*	@param: total - true/false - send records row by row or all at once (for grid only)
	*	@type: public
	*/
	setTransactionMode:function(mode,total){
        this._tMode=mode;
		this._tSend=total;
    },
    escape:function(data){
    	if (this._utf)
    		return encodeURIComponent(data);
    	else
        	return escape(data);
	},
    /**
	* 	@desc: allows to set escaping mode
	*	@param: true - utf based escaping, simple - use current page encoding
	*	@type: public
	*/	
	enableUTFencoding:function(mode){
        this._utf=convertStringToBoolean(mode);
    },
    /**
	* 	@desc: allows to define, which column may trigger update
	*	@param: val - array or list of true/false values
	*	@type: public
	*/
	setDataColumns:function(val){
		this._columns=(typeof val == "string")?val.split(","):val;
    },
    /**
	* 	@desc: get state of updating
	*	@returns:   true - all in sync with server, false - some items not updated yet.
	*	@type: public
	*/
	getSyncState:function(){
		return !this.updatedRows.length;
	},
	/**
	* 	@desc: enable/disable named field for data syncing, will use column ids for grid
	*	@param:   mode - true/false
	*	@type: public
	*/
	enableDataNames:function(mode){
		this._endnm=convertStringToBoolean(mode);
	},
	/**
	* 	@desc: enable/disable mode , when only changed fields and row id send to the server side, instead of all fields in default mode
	*	@param:   mode - true/false
	*	@type: public
	*/
	enablePartialDataSend:function(mode){
		this._changed=convertStringToBoolean(mode);
	},
	/**
	* 	@desc: set if rows should be send to server automaticaly
	*	@param: mode - "row" - based on row selection changed, "cell" - based on cell editing finished, "off" - manual data sending
	*	@type: public
	*/
	setUpdateMode:function(mode,dnd){
		this.autoUpdate = (mode=="cell");
		this.updateMode = mode;
		this.dnd=dnd;
	},
	ignore:function(code,master){
		this._silent_mode=true;
		code.call(master||window);
		this._silent_mode=false;
	},
	/**
	* 	@desc: mark row as updated/normal. check mandatory fields,initiate autoupdate (if turned on)
	*	@param: rowId - id of row to set update-status for
	*	@param: state - true for "updated", false for "not updated"
	*	@param: mode - update mode name
	*	@type: public
	*/
	setUpdated:function(rowId,state,mode){
		if (this._silent_mode) return;
		var ind=this.findRow(rowId);
		
		mode=mode||"updated";
		var existing = this.obj.getUserData(rowId,this.action_param);
		if (existing && mode == "updated") mode=existing;
		if (state){
			this.set_invalid(rowId,false); //clear previous error flag
			this.updatedRows[ind]=rowId;
			this.obj.setUserData(rowId,this.action_param,mode);
			if (this._in_progress[rowId]) 
				this._in_progress[rowId]="wait";
		} else{
			if (!this.is_invalid(rowId)){
				this.updatedRows.splice(ind,1);
				this.obj.setUserData(rowId,this.action_param,"");
			}
		}

		//clear changed flag
		if (!state)
			this._clearUpdateFlag(rowId);
     			
		this.markRow(rowId,state,mode);
		if (state && this.autoUpdate) this.sendData(rowId);
	},
	_clearUpdateFlag:function(id){},
	markRow:function(id,state,mode){ 
		var str="";
		var invalid=this.is_invalid(id);
		if (invalid){
        	str=this.styles[invalid];
        	state=true;
    	}
		if (this.callEvent("onRowMark",[id,state,mode,invalid])){
			//default logic
			str=this.styles[state?mode:"clear"]+str;
			
        	this.obj[this._methods[0]](id,str);

			if (invalid && invalid.details){
				str+=this.styles[invalid+"_cell"];
				for (var i=0; i < invalid.details.length; i++)
					if (invalid.details[i])
        				this.obj[this._methods[1]](id,i,str);
			}
		}
	},
	getState:function(id){
		return this.obj.getUserData(id,this.action_param);
	},
	is_invalid:function(id){
		return this._invalid[id];
	},
	set_invalid:function(id,mode,details){ 
		if (details) mode={value:mode, details:details, toString:function(){ return this.value.toString(); }};
		this._invalid[id]=mode;
	},
	/**
	* 	@desc: check mandatory fields and varify values of cells, initiate update (if specified)
	*	@param: rowId - id of row to set update-status for
	*	@type: public
	*/
	checkBeforeUpdate:function(rowId){ 
		return true;
	},
	/**
	* 	@desc: send row(s) values to server
	*	@param: rowId - id of row which data to send. If not specified, then all "updated" rows will be send
	*	@type: public
	*/
	sendData:function(rowId){
		if (this._waitMode && (this.obj.mytype=="tree" || this.obj._h2)) return;
		if (this.obj.editStop) this.obj.editStop();
	
		
		if(typeof rowId == "undefined" || this._tSend) return this.sendAllData();
		if (this._in_progress[rowId]) return false;
		
		this.messages=[];
		if (!this.checkBeforeUpdate(rowId) && this.callEvent("onValidatationError",[rowId,this.messages])) return false;
		this._beforeSendData(this._getRowData(rowId),rowId);
    },
    _beforeSendData:function(data,rowId){
    	if (!this.callEvent("onBeforeUpdate",[rowId,this.getState(rowId),data])) return false;	
		this._sendData(data,rowId);
    },
    serialize:function(data, id){
    	if (typeof data == "string")
    		return data;
    	if (typeof id != "undefined")
    		return this.serialize_one(data,"");
    	else{
    		var stack = [];
    		var keys = [];
    		for (var key in data)
    			if (data.hasOwnProperty(key)){
    				stack.push(this.serialize_one(data[key],key+this.post_delim));
    				keys.push(key);
				}
    		stack.push("ids="+this.escape(keys.join(",")));
    		return stack.join("&");
    	}
    },
    serialize_one:function(data, pref){
    	if (typeof data == "string")
    		return data;
    	var stack = [];
    	for (var key in data)
    		if (data.hasOwnProperty(key))
    			stack.push(this.escape((pref||"")+key)+"="+this.escape(data[key]));
		return stack.join("&");
    },
    _sendData:function(a1,rowId){
    	if (!a1) return; //nothing to send
		if (!this.callEvent("onBeforeDataSending",rowId?[rowId,this.getState(rowId),a1]:[null, null, a1])) return false;				
		
    	if (rowId)
			this._in_progress[rowId]=(new Date()).valueOf();
		var a2=new dtmlXMLLoaderObject(this.afterUpdate,this,true);
		
		var a3 = this.serverProcessor+(this._user?(getUrlSymbol(this.serverProcessor)+["dhx_user="+this._user,"dhx_version="+this.obj.getUserData(0,"version")].join("&")):"");

		if (this._tMode!="POST")
        	a2.loadXML(a3+((a3.indexOf("?")!=-1)?"&":"?")+this.serialize(a1,rowId));
		else
        	a2.loadXML(a3,true,this.serialize(a1,rowId));

		this._waitMode++;
    },
	sendAllData:function(){
		if (!this.updatedRows.length) return;			

		this.messages=[]; var valid=true;
		for (var i=0; i<this.updatedRows.length; i++)
			valid&=this.checkBeforeUpdate(this.updatedRows[i]);
		if (!valid && !this.callEvent("onValidatationError",["",this.messages])) return false;
	
		if (this._tSend) 
			this._sendData(this._getAllData());
		else
			for (var i=0; i<this.updatedRows.length; i++)
				if (!this._in_progress[this.updatedRows[i]]){
					if (this.is_invalid(this.updatedRows[i])) continue;
					this._beforeSendData(this._getRowData(this.updatedRows[i]),this.updatedRows[i]);
					if (this._waitMode && (this.obj.mytype=="tree" || this.obj._h2)) return; //block send all for tree
				}
	},
    
	
	
	
	
	
	
	
	_getAllData:function(rowId){
		var out={};
		var has_one = false;
		for(var i=0;i<this.updatedRows.length;i++){
			var id=this.updatedRows[i];
			if (this._in_progress[id] || this.is_invalid(id)) continue;
			if (!this.callEvent("onBeforeUpdate",[id,this.getState(id)])) continue;	
			out[id]=this._getRowData(id,id+this.post_delim);
			has_one = true;
			this._in_progress[id]=(new Date()).valueOf();
		}
		return has_one?out:null;
	},
	
	
	/**
	* 	@desc: specify column which value should be varified before sending to server
	*	@param: ind - column index (0 based)
	*	@param: verifFunction - function (object) which should verify cell value (if not specified, then value will be compared to empty string). Two arguments will be passed into it: value and column name
	*	@type: public
	*/
	setVerificator:function(ind,verifFunction){
		this.mandatoryFields[ind] = verifFunction||(function(value){return (value!="");});
	},
	/**
	* 	@desc: remove column from list of those which should be verified
	*	@param: ind - column Index (0 based)
	*	@type: public
	*/
	clearVerificator:function(ind){
		this.mandatoryFields[ind] = false;
	},
	
	
	
	
	
	findRow:function(pattern){
		var i=0;
    	for(i=0;i<this.updatedRows.length;i++)
		    if(pattern==this.updatedRows[i]) break;
	    return i;
    },

   
	


    





	/**
	* 	@desc: define custom actions
	*	@param: name - name of action, same as value of action attribute
	*	@param: handler - custom function, which receives a XMl response content for action
	*	@type: private
	*/
	defineAction:function(name,handler){
        if (!this._uActions) this._uActions=[];
            this._uActions[name]=handler;
	},




	/**
*     @desc: used in combination with setOnBeforeUpdateHandler to create custom client-server transport system
*     @param: sid - id of item before update
*     @param: tid - id of item after up0ate
*     @param: action - action name
*     @type: public
*     @topic: 0
*/
	afterUpdateCallback:function(sid, tid, action, btag) {
		var marker = sid;
		var correct=(action!="error" && action!="invalid");
		if (!correct) this.set_invalid(sid,action);
		if ((this._uActions)&&(this._uActions[action])&&(!this._uActions[action](btag))) 
			return (delete this._in_progress[marker]);
			
		if (this._in_progress[marker]!="wait")
	    	this.setUpdated(sid, false);
	    	
	    var soid = sid;
	
	    switch (action) {
	    case "inserted":
	    case "insert":
	        if (tid != sid) {
	            this.obj[this._methods[2]](sid, tid);
	            sid = tid;
	        }
	        break;
	    case "delete":
	    case "deleted":
	    	this.obj.setUserData(sid, this.action_param, "true_deleted");
	        this.obj[this._methods[3]](sid);
	        delete this._in_progress[marker];
	        return this.callEvent("onAfterUpdate", [sid, action, tid, btag]);
	        break;
	    }
	    
	    if (this._in_progress[marker]!="wait"){
	    	if (correct) this.obj.setUserData(sid, this.action_param,'');
	    	delete this._in_progress[marker];
    	} else {
    		delete this._in_progress[marker];
    		this.setUpdated(tid,true,this.obj.getUserData(sid,this.action_param));
		}
	    
	    this.callEvent("onAfterUpdate", [sid, action, tid, btag]);
	},

	/**
	* 	@desc: response from server
	*	@param: xml - XMLLoader object with response XML
	*	@type: private
	*/
	afterUpdate:function(that,b,c,d,xml){
		xml.getXMLTopNode("data"); //fix incorrect content type in IE
		if (!xml.xmlDoc.responseXML) return;
		var atag=xml.doXPath("//data/action");
		for (var i=0; i<atag.length; i++){
        	var btag=atag[i];
			var action = btag.getAttribute("type");
			var sid = btag.getAttribute("sid");
			var tid = btag.getAttribute("tid");
			
			that.afterUpdateCallback(sid,tid,action,btag);
		}
		that.finalizeUpdate();
	},
	finalizeUpdate:function(){
		if (this._waitMode) this._waitMode--;
		
		if ((this.obj.mytype=="tree" || this.obj._h2) && this.updatedRows.length) 
			this.sendData();
		this.callEvent("onAfterUpdateFinish",[]);
		if (!this.updatedRows.length)
			this.callEvent("onFullSync",[]);
	},




	
	/**
	* 	@desc: initializes data-processor
	*	@param: anObj - dhtmlxGrid object to attach this data-processor to
	*	@type: public
	*/
	init:function(anObj){
		this.obj = anObj;
		if (this.obj._dp_init) 
			this.obj._dp_init(this);
	},
	
	
	setOnAfterUpdate:function(ev){
		this.attachEvent("onAfterUpdate",ev);
	},
	enableDebug:function(mode){
	},
	setOnBeforeUpdateHandler:function(func){  
		this.attachEvent("onBeforeDataSending",func);
	},



	/*! starts autoupdate mode
		@param interval
			time interval for sending update requests
	*/
	setAutoUpdate: function(interval, user) {
		interval = interval || 2000;
		
		this._user = user || (new Date()).valueOf();
		this._need_update = false;
		this._loader = null;
		this._update_busy = false;
		
		this.attachEvent("onAfterUpdate",function(sid,action,tid,xml_node){
			this.afterAutoUpdate(sid, action, tid, xml_node);
		});
		this.attachEvent("onFullSync",function(){
			this.fullSync();
		});
		
		var self = this;
		window.setInterval(function(){
			self.loadUpdate();
		}, interval);
	},


	/*! process updating request answer
		if status == collision version is depricated
		set flag for autoupdating immidiatly
	*/
	afterAutoUpdate: function(sid, action, tid, xml_node) {
		if (action == 'collision') {
			this._need_update = true;
			return false;
		} else {
			return true;
		}
	},


	/*! callback function for onFillSync event
		call update function if it's need
	*/
	fullSync: function() {
		if (this._need_update == true) {
			this._need_update = false;
			this.loadUpdate();
		}
		return true;
	},


	/*! sends query to the server and call callback function
	*/
	getUpdates: function(url,callback){
		if (this._update_busy) 
			return false;
		else
			this._update_busy = true;
		
		this._loader = this._loader || new dtmlXMLLoaderObject(true);
		
		this._loader.async=true;
		this._loader.waitCall=callback;
		this._loader.loadXML(url);
	},


	/*! returns xml node value
		@param node
			xml node
	*/
	_v: function(node) {
		if (node.firstChild) return node.firstChild.nodeValue;
		return "";
	},


	/*! returns values array of xml nodes array
		@param arr
			array of xml nodes
	*/
	_a: function(arr) {
		var res = [];
		for (var i=0; i < arr.length; i++) {
			res[i]=this._v(arr[i]);
		};
		return res;
	},


	/*! loads updates and processes them
	*/
	loadUpdate: function(){
		var self = this;
		var version = this.obj.getUserData(0,"version");
		var url = this.serverProcessor+getUrlSymbol(this.serverProcessor)+["dhx_user="+this._user,"dhx_version="+version].join("&");
		url = url.replace("editing=true&","");
		this.getUpdates(url, function(){
			var vers = self._loader.doXPath("//userdata");
			self.obj.setUserData(0,"version",self._v(vers[0]));
			
			var upds = self._loader.doXPath("//update");
			if (upds.length){
				self._silent_mode = true;
				
				for (var i=0; i<upds.length; i++) {
					var status = upds[i].getAttribute('status');
					var id = upds[i].getAttribute('id');
					var parent = upds[i].getAttribute('parent');
					switch (status) {
						case 'inserted':
							self.callEvent("insertCallback",[upds[i], id, parent]);
							break;
						case 'updated':
							self.callEvent("updateCallback",[upds[i], id, parent]);
							break;
						case 'deleted':
							self.callEvent("deleteCallback",[upds[i], id, parent]);
							break;
					}
				}
				
				self._silent_mode = false;
			}
			
			self._update_busy = false;
			self = null;
		});
	}

};

//(c)dhtmlx ltd. www.dhtmlx.com
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
			if (!this.obj.rowsAr[rowId])
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
		if (!this.obj.rowsAr[sid]) this._log("Incorrect SID, row with such ID not exists in grid");
	}
	this._log("&nbsp;Action: "+action+" SID:"+sid+" TID:"+tid);
},function(){
	
});







/*
	dhx_sort[index]=direction
	dhx_filter[index]=mask
*/
if (window.dhtmlXGridObject){
	dhtmlXGridObject.prototype._init_point_connector=dhtmlXGridObject.prototype._init_point;
	dhtmlXGridObject.prototype._init_point=function(){
		var clear_url=function(url){
			url=url.replace(/(\?|\&)connector[^\f]*/g,"");
			return url+(url.indexOf("?")!=-1?"&":"?")+"connector=true"+(mygrid.hdr.rows.length > 0 ? "&dhx_no_header=1":"");
		};
		var combine_urls=function(url){
			return clear_url(url)+(this._connector_sorting||"")+(this._connector_filter||"");
		};
		var sorting_url=function(url,ind,dir){
			this._connector_sorting="&dhx_sort["+ind+"]="+dir;
			return combine_urls.call(this,url);
		};
		var filtering_url=function(url,inds,vals){
			for (var i=0; i<inds.length; i++)
				inds[i]="dhx_filter["+inds[i]+"]="+encodeURIComponent(vals[i]);
			this._connector_filter="&"+inds.join("&");
			return combine_urls.call(this,url);
		};
		this.attachEvent("onCollectValues",function(ind){
			if (this._con_f_used[ind]){
				if (typeof(this._con_f_used[ind]) == "object")
					return this._con_f_used[ind];
				else
					return false;
			}
			return true;
		});	
		this.attachEvent("onDynXLS",function(){
				this.xmlFileUrl=combine_urls.call(this,this.xmlFileUrl);
				return true;
		});				
		this.attachEvent("onBeforeSorting",function(ind,type,dir){
			if (type=="connector"){
				var self=this;
				this.clearAndLoad(sorting_url.call(this,this.xmlFileUrl,ind,dir),function(){
					self.setSortImgState(true,ind,dir);
				});
				return false;
			}
			return true;
		});
		this.attachEvent("onFilterStart",function(a,b){
			if (this._con_f_used.length){
				this.clearAndLoad(filtering_url.call(this,this.xmlFileUrl,a,b));
				return false;
			}
			return true;
		});
		this.attachEvent("onXLE",function(a,b,c,xml){
			if (!xml) return;
		});
		
		if (this._init_point_connector) this._init_point_connector();
	};
	dhtmlXGridObject.prototype._con_f_used=[];
	dhtmlXGridObject.prototype._in_header_connector_text_filter=function(t,i){
		if (!this._con_f_used[i])
			this._con_f_used[i]=1;
		return this._in_header_text_filter(t,i);
	};
	dhtmlXGridObject.prototype._in_header_connector_select_filter=function(t,i){
		if (!this._con_f_used[i])
			this._con_f_used[i]=2;
		return this._in_header_select_filter(t,i);
	};
	dhtmlXGridObject.prototype.load_connector=dhtmlXGridObject.prototype.load;
	dhtmlXGridObject.prototype.load=function(url, call, type){
		if (!this._colls_loaded && this.cellType){
			var ar=[];
			for (var i=0; i < this.cellType.length; i++)
				if (this.cellType[i].indexOf("co")==0 || this._con_f_used[i]==2) ar.push(i);
			if (ar.length)
				arguments[0]+=(arguments[0].indexOf("?")!=-1?"&":"?")+"connector=true&dhx_colls="+ar.join(",");
		}
		return this.load_connector.apply(this,arguments);
	};
	dhtmlXGridObject.prototype._parseHead_connector=dhtmlXGridObject.prototype._parseHead;
	dhtmlXGridObject.prototype._parseHead=function(url, call, type){
		this._parseHead_connector.apply(this,arguments);
		if (!this._colls_loaded){
			var cols = this.xmlLoader.doXPath("./coll_options", arguments[0]);
			for (var i=0; i < cols.length; i++){
				var f = cols[i].getAttribute("for");
				var v = [];
				var combo=null;
				if (this.cellType[f] == "combo")
					combo = this.getColumnCombo(f);
				if (this.cellType[f].indexOf("co")==0)
					combo=this.getCombo(f);
					
				var os = this.xmlLoader.doXPath("./item",cols[i]);
				for (var j=0; j<os.length; j++){
					var val=os[j].getAttribute("value");
					
					if (combo){
						var lab=os[j].getAttribute("label")||val;
						
						if (combo.addOption)
							combo.addOption([[val, lab]]);
						else
							combo.put(val,lab);
							
						v[v.length]=lab;
					} else
						v[v.length]=val;
				}
				if (this._con_f_used[f*1])
					this._con_f_used[f*1]=v;
			};
			this._colls_loaded=true;
		}
	};	
	
	
	

}

if (window.dataProcessor){
	dataProcessor.prototype.init_original=dataProcessor.prototype.init;
	dataProcessor.prototype.init=function(obj){
		this.init_original(obj);
		obj._dataprocessor=this;
		
		this.setTransactionMode("POST",true);
		this.serverProcessor+=(this.serverProcessor.indexOf("?")!=-1?"&":"?")+"editing=true";
	};
};
dhtmlxError.catchError("LoadXML",function(a,b,c){
	alert(c[0].responseText);
});

window.dhtmlXScheduler=window.scheduler={version:2.2};
dhtmlxEventable(scheduler);
scheduler.init=function(id,date,mode){
	date=date||(new Date());
	mode=mode||"week";
	
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
	})
	
	this.set_sizes();
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
}
scheduler.set_xy=function(node,w,h,x,y){
	node.style.width=Math.max(0,w)+"px";
	node.style.height=Math.max(0,h)+"px";
	if (arguments.length>3){
		node.style.left=x+"px";
		node.style.top=y+"px";	
	}
}
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
}
scheduler.set_actions=function(){
	for (var a in this._els)
		if (this._click[a])
			for (var i=0; i < this._els[a].length; i++)
				this._els[a][i].onclick=scheduler._click[a];
	this._obj.onselectstart=function(e){ return false; }
	this._obj.onmousemove=function(e){
		scheduler._on_mouse_move(e||event);
	}
	this._obj.onmousedown=function(e){
		scheduler._on_mouse_down(e||event);
	}
	this._obj.onmouseup=function(e){
		scheduler._on_mouse_up(e||event);
	}
	this._obj.ondblclick=function(e){
		scheduler._on_dbl_click(e||event);
	}
}
scheduler.select=function(id){
	if (this._table_view || !this.getEvent(id)._timed) return; //temporary block
	if (this._select_id==id) return;
	this.editStop(false);
	this.unselect();
	this._select_id = id;
	this.updateEvent(id);
}
scheduler.unselect=function(id){
	if (id && id!=this._select_id) return;
	var t=this._select_id;
	this._select_id = null;
	if (t) this.updateEvent(t);
}
scheduler.getState=function(){
	return {
		mode: this._mode,
		date: this._date,
		min_date: this._min_date,
		max_date: this._max_date,
		editor_id: this._edit_id,
		lightbox_id: this._lightbox_id
	};
}
scheduler._click={
	dhx_cal_data:function(e){
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
		var mode = this.getAttribute("name").split("_")[0];
		scheduler.setCurrentView(scheduler._date,mode);
	},
	buttons:{
		"delete":function(id){ var c=scheduler.locale.labels.confirm_deleting; if (!c||confirm(c)) scheduler.deleteEvent(id); },
		edit:function(id){ scheduler.edit(id); },
		save:function(id){ scheduler.editStop(true); },
		details:function(id){ scheduler.showLightbox(id); },
		cancel:function(id){ scheduler.editStop(false); }
	}
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
	this._drag_mode="new-size";
	
	this._loading=true;
	this.addEvent(base);
	this.callEvent("onEventCreated",[this._drag_id,e]);
	this._loading=false;
	
	this._drag_event={}; //dummy , to trigger correct event updating logic
	this._on_mouse_up(e);	
}
scheduler._on_dbl_click=function(e,src){
	src = src||(e.target||e.srcElement);
	if (this.config.readonly) return;
	var name = src.className.split(" ")[0];
	switch(name){
		case "dhx_scale_holder":
		case "dhx_scale_holder_now":
		case "dhx_month_body":
			if (!scheduler.config.dblclick_create) break;
			var pos=this._mouse_coords(e);
			var start=this._min_date.valueOf()+(pos.y*this.config.time_step+(this._table_view?0:pos.x)*24*60)*60000;
			start = this._correct_shift(start);
			this.addEventNow(start,null,e);
			break;
		case "dhx_body":
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
}

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
}
scheduler._correct_shift=function(start, back){
	return start-=((new Date(scheduler._min_date)).getTimezoneOffset()-(new Date(start)).getTimezoneOffset())*60000*(back?-1:1);	
}
scheduler._on_mouse_move=function(e){
	if (this._drag_mode){
		var pos=this._mouse_coords(e);
		if (!this._drag_pos || this._drag_pos.x!=pos.x || this._drag_pos.y!=pos.y){
			
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
				if (this._table_view)
					end = this._min_date.valueOf()+pos.y*this.config.time_step*60000 + (pos.custom?0:24*60*60000);
				else{
					end = this.date.date_part(new Date(ev.end_date)).valueOf()+pos.y*this.config.time_step*60000;
					this._els["dhx_cal_data"][0].style.cursor="s-resize";
					if (this._mode == "week" || this._mode == "day")
						end = this._correct_shift(end);
				}
				if (this._drag_mode == "new-size"){ 
					if (end <= this._drag_start){
						var shift = pos.shift||((this._table_view && !pos.custom)?24*60*60000:0);
						start = end-shift;
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
			if (this._table_view || (new_end.getDate()==new_start.getDate() && new_end.getHours()<this.config.last_hour)){
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
}
scheduler._on_mouse_context=function(e,src){
	return this.callEvent("onContextMenu",[this._locate_event(src),e]);
}
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
			this._drag_event=this._copy_event(this.getEvent(this._drag_id)||{});
		}
	}
	this._drag_start=null;
}
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
					ev.start_date = this._drag_event.start_date;
					ev.end_date = this._drag_event.end_date;
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
}	
scheduler.update_view=function(){
	//this.set_sizes();
	this._reset_scale();
	if (this._load_mode && this._load()) return this._render_wait = true;
	this.render_view_data();
}
scheduler.setCurrentView=function(date,mode){
	
	if (!this.callEvent("onBeforeViewChange",[this._mode,this._date,mode,date])) return;
	//hide old custom view
	if (this[this._mode+"_view"] && mode && this._mode!=mode)
		this[this._mode+"_view"](false);
		
	this._close_not_saved();
	
	this._mode=mode||this._mode;
	this._date=date;
	this._table_view=(this._mode=="month");
	
	var tabs=this._els["dhx_cal_tab"];
	for (var i=0; i < tabs.length; i++) {
		tabs[i].className="dhx_cal_tab"+((tabs[i].getAttribute("name")==this._mode+"_tab")?" active":"");
	};
	
	//show new view
	var view=this[this._mode+"_view"];
	view?view(true):this.update_view();
	
	this.callEvent("onViewChange",[this._mode,this._date]);
}
scheduler._render_x_header = function(i,left,d,h){
	//header scale	
	var head=document.createElement("DIV"); head.className="dhx_scale_bar";
	this.set_xy(head,this._cols[i]-1,this.xy.scale_height-2,left,0);//-1 for border
	head.innerHTML=this.templates[this._mode+"_scale_date"](d,this._mode); //TODO - move in separate method
	h.appendChild(head);
}
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
		}
		
		d=this.date.add(d,1,"day")
		summ-=this._cols[i];
		left+=this._cols[i];
		this._colsS[i]=(this._cols[i-1]||0)+(this._colsS[i-1]||(this._table_view?0:this.xy.scale_width+2));
	}
	this._max_date=d;
	this._colsS[count]=this._cols[count-1]+this._colsS[count-1];
	
	if (this._table_view)
		this._reset_month_scale(b,dd,sd);
	else{
		this._reset_hours_scale(b,dd,sd);
		if (c.multi_day){
			var c1 = document.createElement("DIV");
			c1.className="dhx_multi_day";
			c1.style.visibility="hidden";
			this.set_xy(c1,parseInt(h.style.width),0,this.xy.scale_width,0);
			b.appendChild(c1);
			var c2 = c1.cloneNode(true);
			c2.className="dhx_multi_day_icon";
			c2.style.visibility="hidden";
			this.set_xy(c2,this.xy.scale_width-1,0,0,0);
			b.appendChild(c2);
			
			this._els["dhx_multi_day"]=[c1,c2];
		}
	}
}
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
}
scheduler._reset_month_scale=function(b,dd,sd){
	var ed=scheduler.date.add(dd,1,"month");
	
	//trim time part for comparation reasons
	var cd=new Date();
	this.date.date_part(cd);
	this.date.date_part(sd);
	
	var rows=Math.ceil((ed.valueOf()-sd.valueOf())/(60*60*24*1000*7));
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
				html+="><div class='dhx_month_head'>"+this.templates.month_day(sd)+"</div><div class='dhx_month_body' "+tdcss[j]+"></div></td>"
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
}
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
scheduler.date={
	date_part:function(date){
		date.setHours(0);
		date.setMinutes(0);
		date.setSeconds(0);
		date.setMilliseconds(0);	
		return date;
	},
	time_part:function(date){
		return (date.valueOf()/1000 - date.getTimezoneOffset()*60)%86400;
	},
	week_start:function(date){
			var shift=date.getDay();
			if (scheduler.config.start_on_monday){
				if (shift==0) shift=6
				else shift--;
			}
			return this.date_part(this.add(date,-1*shift,"day"));
	},
	month_start:function(date){
		date.setDate(1);
		return this.date_part(date);
	},
	year_start:function(date){
		date.setMonth(0);
		return this.month_start(date);
	},
	day_start:function(date){
			return this.date_part(date);
	},
	add:function(date,inc,mode){
		var ndate=new Date(date.valueOf());
		switch(mode){
			case "day": ndate.setDate(ndate.getDate()+inc); break;
			case "week": ndate.setDate(ndate.getDate()+7*inc); break;
			case "month": ndate.setMonth(ndate.getMonth()+inc); break;
			case "year": ndate.setYear(ndate.getFullYear()+inc); break;
			case "hour": ndate.setHours(ndate.getHours()+inc); break;
			case "minute": ndate.setMinutes(ndate.getMinutes()+inc); break;
			default:
				return scheduler.date["add_"+mode](date,inc,mode);
		}
		return ndate;
	},
	to_fixed:function(num){
		if (num<10)	return "0"+num;
		return num;
	},
	copy:function(date){
		return new Date(date.valueOf());
	},
	date_to_str:function(format,utc){
		format=format.replace(/%[a-zA-Z]/g,function(a){
			switch(a){
				case "%d": return "\"+scheduler.date.to_fixed(date.getDate())+\"";
				case "%m": return "\"+scheduler.date.to_fixed((date.getMonth()+1))+\"";
				case "%j": return "\"+date.getDate()+\"";
				case "%n": return "\"+(date.getMonth()+1)+\"";
				case "%y": return "\"+scheduler.date.to_fixed(date.getFullYear()%100)+\""; 
				case "%Y": return "\"+date.getFullYear()+\"";
				case "%D": return "\"+scheduler.locale.date.day_short[date.getDay()]+\"";
				case "%l": return "\"+scheduler.locale.date.day_full[date.getDay()]+\"";
				case "%M": return "\"+scheduler.locale.date.month_short[date.getMonth()]+\"";
				case "%F": return "\"+scheduler.locale.date.month_full[date.getMonth()]+\"";
				case "%h": return "\"+scheduler.date.to_fixed((date.getHours()+11)%12+1)+\"";
				case "%g": return "\"+((date.getHours()+11)%12+1)+\"";
				case "%G": return "\"+date.getHours()+\"";
				case "%H": return "\"+scheduler.date.to_fixed(date.getHours())+\"";
				case "%i": return "\"+scheduler.date.to_fixed(date.getMinutes())+\"";
				case "%a": return "\"+(date.getHours()>11?\"pm\":\"am\")+\"";
				case "%A": return "\"+(date.getHours()>11?\"PM\":\"AM\")+\"";
				case "%s": return "\"+scheduler.date.to_fixed(date.getSeconds())+\"";
				case "%W": return "\"+scheduler.date.to_fixed(scheduler.date.getISOWeek(date))+\"";
				default: return a;
			}
		})
		if (utc) format=format.replace(/date\.get/g,"date.getUTC");
		return new Function("date","return \""+format+"\";");
	},
	str_to_date:function(format,utc){
		var splt="var temp=date.split(/[^0-9a-zA-Z]+/g);";
		var mask=format.match(/%[a-zA-Z]/g);
		for (var i=0; i<mask.length; i++){
			switch(mask[i]){
				case "%j":
				case "%d": splt+="set[2]=temp["+i+"]||1;";
					break;
				case "%n":
				case "%m": splt+="set[1]=(temp["+i+"]||1)-1;";
					break;
				case "%y": splt+="set[0]=temp["+i+"]*1+(temp["+i+"]>50?1900:2000);";
					break;
				case "%g":
				case "%G":
				case "%h": 
				case "%H":
							splt+="set[3]=temp["+i+"]||0;";
					break;
				case "%i":
							splt+="set[4]=temp["+i+"]||0;";
					break;
				case "%Y":  splt+="set[0]=temp["+i+"]||0;";
					break;
				case "%a":					
				case "%A":  splt+="set[3]=set[3]%12+((temp["+i+"]||'').toLowerCase()=='am'?0:12);";
					break;					
				case "%s":  splt+="set[5]=temp["+i+"]||0;";
					break;
			}
		}
		var code ="set[0],set[1],set[2],set[3],set[4],set[5]";
		if (utc) code =" Date.UTC("+code+")";
		return new Function("date","var set=[0,0,1,0,0,0]; "+splt+" return new Date("+code+");");
	},
		
	getISOWeek: function(ndate) {
		if(!ndate) return false;
		var nday = ndate.getDay();
		if (nday == 0) {
			nday = 7;
		}
		var first_thursday = new Date(ndate.valueOf());
		first_thursday.setDate(ndate.getDate() + (4 - nday));
		var year_number = first_thursday.getFullYear(); // year of the first Thursday
		var ordinal_date = Math.floor( (first_thursday.getTime() - new Date(year_number, 0, 1).getTime()) / 86400000); //ordinal date of the first Thursday - 1 (so not really ordinal date)
		var week_number = 1 + Math.floor( ordinal_date / 7);	
		return week_number;
	},
	
	getUTCISOWeek: function(ndate){
   	return this.getISOWeek(ndate);
   }
}

scheduler.locale={
	date:{
		month_full:["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
		month_short:["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
		day_full:["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    	day_short:["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    },
    labels:{
    	dhx_cal_today_button:"Today",
    	day_tab:"Day",
    	week_tab:"Week",
    	month_tab:"Month",
    	new_event:"New event",
		icon_save:"Save",
		icon_cancel:"Cancel",
		icon_details:"Details",
		icon_edit:"Edit",
		icon_delete:"Delete",
		confirm_closing:"",//Your changes will be lost, are your sure ?
		confirm_deleting:"Event will be deleted permanently, are you sure?",
		section_description:"Description",
		section_time:"Time period",
		full_day:"Full day",
		
		/*recurring events*/
		confirm_recurring:"Do you want to edit the whole set of repeated events?",
		section_recurring:"Repeat event",
		button_recurring:"Disabled",
		button_recurring_open:"Enabled",
		
		/*agenda view extension*/
		agenda_tab:"Agenda",
		date:"Date",
		description:"Description",
		
		/*year view extension*/
		year_tab:"Year"
    }
}


/*
%e	Day of the month without leading zeros (01..31)
%d	Day of the month, 2 digits with leading zeros (01..31)
%j	Day of the year, 3 digits with leading zeros (001..366)
%a	A textual representation of a day, two letters
%W	A full textual representation of the day of the week

%c	Numeric representation of a month, without leading zeros (0..12)
%m	Numeric representation of a month, with leading zeros (00..12)
%b	A short textual representation of a month, three letters (Jan..Dec)
%M	A full textual representation of a month, such as January or March (January..December)

%y	A two digit representation of a year (93..03)
%Y	A full numeric representation of a year, 4 digits (1993..03)
*/

scheduler.config={
	default_date: "%j %M %Y",
	month_date: "%F %Y",
	load_date: "%Y-%m-%d",
	week_date: "%l",
	day_date: "%D, %F %j",
	hour_date: "%H:%i",
	month_day : "%d",
	xml_date:"%m/%d/%Y %H:%i",
	api_date:"%d-%m-%Y %H:%i",

	hour_size_px:42,
	time_step:5,

	start_on_monday:1,
	first_hour:0,
	last_hour:24,
	readonly:false,
	drag_resize:1,
	drag_move:1,
	drag_create:1,
	dblclick_create:1,
	edit_on_create:1,
	details_on_create:0,
	click_form_details:0,
	
	server_utc:false,

	positive_closing:false,

	icons_edit:["icon_save","icon_cancel"],
	icons_select:["icon_details","icon_edit","icon_delete"],
	
	lightbox:{
		sections:[	{name:"description", height:200, map_to:"text", type:"textarea" , focus:true},
					{name:"time", height:72, type:"time", map_to:"auto"}	]
	}
};
scheduler.templates={}
scheduler.init_templates=function(){
	var d=scheduler.date.date_to_str;
	var c=scheduler.config;
	var f = function(a,b){
		for (var c in b)
			if (!a[c]) a[c]=b[c];
	}
	f(scheduler.templates,{
		day_date:d(c.default_date),
		month_date:d(c.month_date),
		week_date:function(d1,d2){
			return scheduler.templates.day_date(d1)+" &ndash; "+scheduler.templates.day_date(scheduler.date.add(d2,-1,"day"));
		},
		day_scale_date:d(c.default_date),
		month_scale_date:d(c.week_date),
		week_scale_date:d(c.day_date),
		hour_scale:d(c.hour_date),
		time_picker:d(c.hour_date),
		event_date:d(c.hour_date),
		month_day:d(c.month_day),
		xml_date:scheduler.date.str_to_date(c.xml_date,c.server_utc),
		load_format:d(c.load_date,c.server_utc),
		xml_format:d(c.xml_date,c.server_utc),
		api_date:scheduler.date.str_to_date(c.api_date),
		event_header:function(start,end,ev){
			return scheduler.templates.event_date(start)+" - "+scheduler.templates.event_date(end);
		},
		event_text:function(start,end,ev){
			return ev.text;
		},
		event_class:function(start,end,ev){
			return "";
		},
		month_date_class:function(d){
			return "";
		},
		week_date_class:function(d){
			return "";
		},
		event_bar_date:function(start,end,ev){
			return scheduler.templates.event_date(start)+" ";
		},
		event_bar_text:function(start,end,ev){
			return ev.text;
		}
	});
	this.callEvent("onTemplatesReady",[])
}



scheduler.uid=function(){
	if (!this._seed) this._seed=(new Date).valueOf();
	return this._seed++;
};
scheduler._events={};
scheduler.clearAll=function(){
	this._events={};
	this._loaded={};
	this.clear_view();
};
scheduler.addEvent=function(start_date,end_date,text,id,extra_data){
	var ev=start_date;
	if (arguments.length!=1){
		ev=extra_data||{};
		ev.start_date=start_date;
		ev.end_date=end_date;
		ev.text=text;
		ev.id=id;
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
scheduler.deleteEvent=function(id,silent){ 
	var ev=this._events[id];
	if (!silent && !this.callEvent("onBeforeEventDelete",[id,ev])) return;
	
	if (ev){
		delete this._events[id];
		this.unselect(id);
		this.event_updated(ev);
	}
};
scheduler.getEvent=function(id){
	return this._events[id];
};
scheduler.setEvent=function(id,hash){
	this._events[id]=hash;
};
scheduler.for_rendered=function(id,method){
	for (var i=this._rendered.length-1; i>=0; i--)
		if (this._rendered[i].getAttribute("event_id")==id)
			method(this._rendered[i],i);
};
scheduler.changeEventId=function(id,new_id){
	if (id == new_id) return;
	var ev=this._events[id];
	if (ev){
		ev.id=new_id;
		this._events[new_id]=ev;
		delete this._events[id];
	}
	this.for_rendered(id,function(r){
		r.setAttribute("event_id",new_id);
	});
	if (this._select_id==id) this._select_id=new_id;
	if (this._edit_id==id) this._edit_id=new_id;
	this.callEvent("onEventIdChange",[id,new_id]);
};

(function(){
	var attrs=["text","Text","start_date","StartDate","end_date","EndDate"];
	var create_getter=function(name){
		return function(id){ return (scheduler.getEvent(id))[name]; };
	};
	var create_setter=function(name){
		return function(id,value){ 
			var ev=scheduler.getEvent(id); ev[name]=value; 
			ev._changed=true; 
			ev._timed=this.is_one_day_event(ev);
			scheduler.event_updated(ev,true); 
		};
	};
	for (var i=0; i<attrs.length; i+=2){
		scheduler["getEvent"+attrs[i+1]]=create_getter(attrs[i]);
		scheduler["setEvent"+attrs[i+1]]=create_setter(attrs[i]);
	}
})();

scheduler.event_updated=function(ev,force){
	if (this.is_visible_events(ev))
		this.render_view_data();
	else this.clear_event(ev.id);
};
scheduler.is_visible_events=function(ev){
	if (ev.start_date<this._max_date && this._min_date<ev.end_date) return true;
	return false;
};
scheduler.is_one_day_event=function(ev){
	var delta = ev.end_date.getDate()-ev.start_date.getDate();
	
	if (!delta)
		return ev.start_date.getMonth()==ev.end_date.getMonth() && ev.start_date.getFullYear()==ev.end_date.getFullYear();
	else {
		if (delta < 0)  delta = Math.ceil((ev.end_date.valueOf()-ev.start_date.valueOf())/(24*60*60*1000));
		return (delta == 1 && !ev.end_date.getHours() && !ev.end_date.getMinutes() && (ev.start_date.getHours() || ev.start_date.getMinutes() ));
	}
		
};
scheduler.get_visible_events=function(){
	//not the best strategy for sure
	var stack=[];
	var filter = this["filter_"+this._mode];
	
	for( var id in this._events)
		if (this.is_visible_events(this._events[id]))
			if (this._table_view || this.config.multi_day || this._events[id]._timed)
				if (!filter || filter(id,this._events[id]))
					stack.push(this._events[id]);
				
	return stack;
};
scheduler.render_view_data=function(){
	if (this._not_render) {
		this._render_wait=true;
		return;
	}
	this._render_wait=false;
	
	this.clear_view();
	var evs=this.get_visible_events();
	
	if (this.config.multi_day && !this._table_view){
		var tvs = [];
		var tvd = [];
		for (var i=0; i < evs.length; i++){
			if (evs[i]._timed)
				tvs.push(evs[i]);
			else
				tvd.push(evs[i]);
		};
		this._table_view=true;
		this.render_data(tvd);
		this._table_view=false;		
		this.render_data(tvs);
	} else 
		this.render_data(evs);	
};
scheduler.render_data=function(evs,hold){
	evs=this._pre_render_events(evs,hold);
	for (var i=0; i<evs.length; i++)
		if (this._table_view)
			this.render_event_bar(evs[i]);
		else
			this.render_event(evs[i]);
};
scheduler._pre_render_events=function(evs,hold){
	var hb = this.xy.bar_height;
	var h_old = this._colsS.heights;	
	var h=this._colsS.heights=[0,0,0,0,0,0,0];
	
	if (!this._table_view) evs=this._pre_render_events_line(evs,hold); //ignore long events for now
	else evs=this._pre_render_events_table(evs,hold);
	
	if (this._table_view){
		if (hold)
			this._colsS.heights = h_old;
		else {
			var evl = this._els["dhx_cal_data"][0].firstChild;
			if (evl.rows){
				for (var i=0; i<evl.rows.length; i++){
					h[i]++;
					if ((h[i])*hb > this._colsS.height-22){ // 22 - height of cell's header
						//we have overflow, update heights
						var cells = evl.rows[i].cells;
						for (var j=0; j < cells.length; j++) {
							cells[j].childNodes[1].style.height = h[i]*hb+"px";
						}
						h[i]=(h[i-1]||0)+cells[0].offsetHeight;
					}
					h[i]=(h[i-1]||0)+evl.rows[i].cells[0].offsetHeight;
				}	
				h.unshift(0);
				if (evl.parentNode.offsetHeight<evl.parentNode.scrollHeight && !evl._h_fix){
					//we have v-scroll, decrease last day cell
					for (var i=0; i<evl.rows.length; i++){
						var cell = evl.rows[i].cells[6].childNodes[0];
						var w = cell.offsetWidth-scheduler.xy.scroll_width+"px";
						cell.style.width = w;
						cell.nextSibling.style.width = w;
					}		
					evl._h_fix=true;
				}
			} else{
				
				if (!evs.length && this._els["dhx_multi_day"][0].style.visibility == "visible")
					h[0]=-1;
				if (evs.length || h[0]==-1){
					//shift days to have space for multiday events
					var childs = evl.parentNode.childNodes;
					var dh = (h[0]+1)*hb+"px";
					for (var i=0; i<childs.length; i++)
						if (this._colsS[i])
							childs[i].style.top=dh;
					var last = this._els["dhx_multi_day"][0];
					last.style.top = "0px";
					last.style.height=dh;
					last.style.visibility=(h[0]==-1?"hidden":"visible");
					last=this._els["dhx_multi_day"][1];
					last.style.height=dh;
					last.style.visibility=(h[0]==-1?"hidden":"visible");
					last.className=h[0]?"dhx_multi_day_icon":"dhx_multi_day_icon_small";
					
					this._dy_shift=(h[0]+1)*hb;
					h[0] = 0;
				}				
				
			}
		}
	}
	
	return evs;
};
scheduler._get_event_sday=function(ev){
	return Math.floor((ev.start_date.valueOf()-this._min_date.valueOf())/(24*60*60*1000));
};
scheduler._pre_render_events_line=function(evs,hold){
	evs.sort(function(a,b){ return a.start_date>b.start_date?1:-1; });
	var days=[]; //events by weeks
	var evs_originals = [];
	for (var i=0; i < evs.length; i++) {
		var ev=evs[i];

		//check scale overflow
		var sh = ev.start_date.getHours();
		var eh = ev.end_date.getHours();
		
		ev._sday=this._get_event_sday(ev);
		if (!days[ev._sday]) days[ev._sday]=[];
		
		if (!hold){
			ev._inner=false;
			var stack=days[ev._sday];
			while (stack.length && stack[stack.length-1].end_date<=ev.start_date)
				stack.splice(stack.length-1,1);
			if (stack.length) stack[stack.length-1]._inner=true;
			ev._sorder=stack.length; stack.push(ev);
			if (stack.length>(stack.max_count||0)) stack.max_count=stack.length;
		}
		
		if (sh < this.config.first_hour || eh >= this.config.last_hour){
			evs_originals.push(ev);
			evs[i]=ev=this._copy_event(ev);
			if (sh < this.config.first_hour){
				ev.start_date.setHours(this.config.first_hour);
				ev.start_date.setMinutes(0);
			}
			if (eh >= this.config.last_hour){
				ev.end_date.setMinutes(0);
				ev.end_date.setHours(this.config.last_hour);
			}
			if (ev.start_date>ev.end_date || sh==this.config.last_hour) {
				evs.splice(i,1); i--; continue;
			}
		}
				
	}
	if (!hold){
		for (var i=0; i < evs.length; i++) 
			evs[i]._count=days[evs[i]._sday].max_count;
		for (var i=0; i < evs_originals.length; i++) 
			evs_originals[i]._count=days[evs_originals[i]._sday].max_count;
	}
	
	return evs;
};
scheduler._time_order=function(evs){
	evs.sort(function(a,b){ 
		if (a.start_date.valueOf()==b.start_date.valueOf()){
			if (a._timed && !b._timed) return 1;
			if (!a._timed && b._timed) return -1;
			return 0;
		}
		return a.start_date>b.start_date?1:-1;
	});
};
scheduler._pre_render_events_table=function(evs,hold){ // max - max height of week slot
	this._time_order(evs);
	
	var out=[];
	var weeks=[[],[],[],[],[],[],[]]; //events by weeks
	var max = this._colsS.heights;
	var start_date;
	var cols = this._cols.length;
	
	for (var i=0; i < evs.length; i++) {
		var ev=evs[i];
		var sd = (start_date||ev.start_date);
		var ed = ev.end_date;
		//trim events which are crossing through current view
		if (sd<this._min_date) sd=this._min_date;
		if (ed>this._max_date) ed=this._max_date;
		
		var locate_s = this.locate_holder_day(sd,false,ev);
		ev._sday=locate_s%cols;
		var locate_e = this.locate_holder_day(ed,true,ev)||cols;
		ev._eday=(locate_e%cols)||cols; //cols used to fill full week, when event end on monday
		ev._length=locate_e-locate_s;
		
		//3600000 - compensate 1 hour during winter|summer time shift
		ev._sweek=Math.floor((this._correct_shift(sd.valueOf(),1)-this._min_date.valueOf())/(60*60*1000*24*cols)); 	
		
		//current slot
		var stack=weeks[ev._sweek];
		//check order position
		var stack_line;
		
		for (stack_line=0; stack_line<stack.length; stack_line++)
			if (stack[stack_line]._eday<=ev._sday)
				break;
		ev._sorder=stack_line; 
		
		
		if (ev._sday+ev._length<=cols){
			start_date=null;
			out.push(ev);
			stack[stack_line]=ev;
			//get max height of slot
			max[ev._sweek]=stack.length-1;
		} else{ // split long event in chunks
			var copy=this._copy_event(ev);
			copy._length=cols-ev._sday;
			copy._eday=cols; copy._sday=ev._sday;
			copy._sweek=ev._sweek; copy._sorder=ev._sorder;
			copy.end_date=this.date.add(sd,copy._length,"day");
			
			out.push(copy);
			stack[stack_line]=copy;
			start_date=copy.end_date;
			//get max height of slot
			max[ev._sweek]=stack.length-1;
			i--; continue;  //repeat same step
		}
	};
	
	return out;
};
scheduler._copy_dummy=function(){ 
	this.start_date=new Date(this.start_date);
	this.end_date=new Date(this.end_date);
};
scheduler._copy_event=function(ev){
	this._copy_dummy.prototype = ev;
	return new this._copy_dummy();
	//return {start_date:ev.start_date, end_date:ev.end_date, text:ev.text, id:ev.id}
};
scheduler._rendered=[];
scheduler.clear_view=function(){
	for (var i=0; i<this._rendered.length; i++){
		var obj=this._rendered[i];
		if (obj.parentNode) obj.parentNode.removeChild(obj);		
	}
	this._rendered=[];
};
scheduler.updateEvent=function(id){
	var ev=this.getEvent(id);
	this.clear_event(id);
	if (ev && this.is_visible_events(ev)) 
		this.render_data([ev],true);
};
scheduler.clear_event=function(id){
	this.for_rendered(id,function(node,i){
		if (node.parentNode)
			node.parentNode.removeChild(node);
		scheduler._rendered.splice(i,1);
	});
};
scheduler.render_event=function(ev){
	var menu = scheduler.xy.menu_width;
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
	if (this._edit_id==ev.id){
		d.style.zIndex = 1; //fix overlapping issue
		width=Math.max(width-4,scheduler.xy.editor_width);
		var d=document.createElement("DIV");
		d.setAttribute("event_id",ev.id);
		this.set_xy(d,width,height-20,left,top+14);
		d.className="dhx_cal_editor";
			
		var d2=document.createElement("DIV");
		this.set_xy(d2,width-6,height-26);
		d2.style.cssText+=";margin:2px 2px 2px 2px;overflow:hidden;";
		
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
		//d.style.zIndex = 1; //fix overlapping issue
		var icons=this.config["icons_"+((this._edit_id==ev.id)?"edit":"select")];
		var icons_str="";
		for (var i=0; i<icons.length; i++)
			icons_str+="<div class='dhx_menu_icon "+icons[i]+"' title='"+this.locale.labels[icons[i]]+"'></div>";
		var obj = this._render_v_bar(ev.id,left-menu+1,top,menu,icons.length*20+26,"","<div class='dhx_menu_head'></div>",icons_str,true);
		obj.style.left=left-menu+1;
		this._els["dhx_cal_data"][0].appendChild(obj);
		this._rendered.push(obj);
	}
};
scheduler._render_v_bar=function(id,x,y,w,h,style,contentA,contentB,bottom){
	var d=document.createElement("DIV");
	
	var ev = this.getEvent(id);
	var cs = "dhx_cal_event";
	var cse = scheduler.templates.event_class(ev.start_date,ev.end_date,ev);
	if (cse) cs=cs+" "+cse;
	
	var html='<div event_id="'+id+'" class="'+cs+'" style="position:absolute; top:'+y+'px; left:'+x+'px; width:'+(w-4)+'px; height:'+h+'px;'+(style||"")+'">';
	html+='<div class="dhx_header" style=" width:'+(w-6)+'px;" >&nbsp;</div>';
	html+='<div class="dhx_title">'+contentA+'</div>';
	html+='<div class="dhx_body" style=" width:'+(w-(this._quirks?4:14))+'px; height:'+(h-(this._quirks?20:30))+'px;">'+contentB+'</div>';
	html+='<div class="dhx_footer" style=" width:'+(w-8)+'px;'+(bottom?' margin-top:-1px;':'')+'" ></div></div>';
	
	d.innerHTML=html;
	return d.firstChild;
};
scheduler.locate_holder=function(day){
	if (this._mode=="day") return this._els["dhx_cal_data"][0].firstChild; //dirty
	return this._els["dhx_cal_data"][0].childNodes[day];
};
scheduler.locate_holder_day=function(date,past){
	var day = Math.floor((this._correct_shift(date,1)-this._min_date)/(60*60*24*1000));
	//when locating end data of event , we need to use next day if time part was defined
	if (past && this.date.time_part(date)) day++;
	return day;
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
	var cse = scheduler.templates.event_class(ev.start_date,ev.end_date,ev);
	if (cse) cs=cs+" "+cse; 
	
	var html='<div event_id="'+ev.id+'" class="'+cs+'" style="position:absolute; top:'+y+'px; left:'+x+'px; width:'+(x2-x-15)+'px;'+(ev._text_style||"")+'">';
		
	if (ev._timed)
		html+=scheduler.templates.event_bar_date(ev.start_date,ev.end_date,ev);
	html+=scheduler.templates.event_bar_text(ev.start_date,ev.end_date,ev)+'</div>';
	html+='</div>';
	
	d.innerHTML=html;
	
	this._rendered.push(d.firstChild);
	parent.appendChild(d.firstChild);
};

scheduler._locate_event=function(node){
	var id=null;
	while (node && !id && node.getAttribute){
		id=node.getAttribute("event_id"); 
		node=node.parentNode;
	}
	return id;
};


scheduler.edit=function(id){
	if (this._edit_id==id) return;
	this.editStop(false,id);
	this._edit_id=id;
	this.updateEvent(id);
};
scheduler.editStop=function(mode,id){
	if (id && this._edit_id==id) return;
	var ev=this.getEvent(this._edit_id);
	if (ev){
		if (mode) ev.text=this._editor.value;
		this._edit_id=null;
		this._editor=null;	
		this.updateEvent(ev.id);
		this._edit_stop_event(ev,mode);
	}
};
scheduler._edit_stop_event=function(ev,mode){
	if (this._new_event){
		if (!mode) this.deleteEvent(ev.id,true);		
		else this.callEvent("onEventAdded",[ev.id,ev]);
		this._new_event=null;
	} else
		if (mode) this.callEvent("onEventChanged",[ev.id,ev]);
};

scheduler.getEvents = function(from,to){
	var result = [];
	for (var a in this._events){
		var ev = this._events[a];
		if (ev && ev.start_date<to && ev.end_date>from)
			result.push(ev);
	}
	return result;
};
scheduler._loaded={};
scheduler._load=function(url,from){
	url=url||this._load_url;
	url+=(url.indexOf("?")==-1?"?":"&")+"timeshift="+(new Date()).getTimezoneOffset();
	if (this.config.prevent_cache)	url+="&uid="+this.uid();
	var to;
	from=from||this._date;
	
	if (this._load_mode){
		var lf = this.templates.load_format;
		
		from = this.date[this._load_mode+"_start"](new Date(from.valueOf()));
		while (from>this._min_date) from=this.date.add(from,-1,this._load_mode);
		to = from;
		
		var cache_line = true;
		while (to<this._max_date){
			to=this.date.add(to,1,this._load_mode);	
			if (this._loaded[lf(from)] && cache_line) 
				from=this.date.add(from,1,this._load_mode);	
			else cache_line = false;
		}
		
		var temp_to=to;
		do {
			to = temp_to;
			temp_to=this.date.add(to,-1,this._load_mode);
		} while (temp_to>from && this._loaded[lf(temp_to)]);
			
		if (to<=from) 
			return false; //already loaded
		dhtmlxAjax.get(url+"&from="+lf(from)+"&to="+lf(to),function(l){scheduler.on_load(l);});
		while(from<to){
			this._loaded[lf(from)]=true;
			from=this.date.add(from,1,this._load_mode);	
		}
	} else
		dhtmlxAjax.get(url,function(l){scheduler.on_load(l);});
	this.callEvent("onXLS",[]);
	return true;
}
scheduler.on_load=function(loader){
	this._loading=true;
	if (this._process)
		var evs=this[this._process].parse(loader.xmlDoc.responseText);
	else
		var evs=this._magic_parser(loader);
	
	this._not_render=true;
	for (var i=0; i<evs.length; i++){
		if (!this.callEvent("onEventLoading",[evs[i]])) continue;
		this.addEvent(evs[i]);
	}
	this._not_render=false;
	if (this._render_wait) this.render_view_data();
	
	if (this._after_call) this._after_call();
	this._after_call=null;
	this._loading=false;
	this.callEvent("onXLE",[]);
}
scheduler.json={};
scheduler.json.parse = function(data){
	if (typeof data == "string"){
		eval("scheduler._temp = "+data+";");
		data = scheduler._temp;
	}
	var evs = [];
	for (var i=0; i < data.length; i++){
		data[i].start_date = scheduler.templates.xml_date(data[i].start_date);
		data[i].end_date = scheduler.templates.xml_date(data[i].end_date);
		evs.push(data[i]);
	}
	return evs;
}
scheduler.parse=function(data,type){
	this._process=type;
	this.on_load({xmlDoc:{responseText:data}});
}
scheduler.load=function(url,call){
	if (typeof call == "string"){
		this._process=call;
		call = arguments[2];
	}
	
	this._load_url=url;
	this._after_call=call;
	this._load(url,this._date);
};
//possible values - day,week,month,year,all
scheduler.setLoadMode=function(mode){
	if (mode=="all") mode="";
	this._load_mode=mode;
};

//current view by default, or all data if "true" as parameter provided
scheduler.refresh=function(refresh_all){
	alert("not implemented");
	/*
	this._loaded={};
	this._load();
	*/
}
scheduler.serverList=function(name){
	return this.serverList[name] = (this.serverList[name]||[]);
}

scheduler._userdata={};
scheduler._magic_parser=function(loader){
	if (!loader.getXMLTopNode){ //from a string
		var xml_string = loader.xmlDoc.responseText;
		loader = new dtmlXMLLoaderObject(function(){});
		loader.loadXMLString(xml_string);
	}
	
	var xml=loader.getXMLTopNode("data");
	if (xml.tagName!="data") return [];//not an xml
	
	var opts = loader.doXPath("//coll_options");
	for (var i=0; i < opts.length; i++) {
		var bind = opts[i].getAttribute("for");
		var arr = this.serverList[bind];
		if (!arr) continue;
		arr.splice(0,arr.length);	//clear old options
		var itms = loader.doXPath(".//item",opts[i]);
		for (var j=0; j < itms.length; j++)
			arr.push({ key:itms[j].getAttribute("value"), label:itms[j].getAttribute("label")});
	}
	if (opts.length)
		scheduler.callEvent("onOptionsLoad",[]);
	
	var ud=loader.doXPath("//userdata");	
	for (var i=0; i < ud.length; i++) {
		var udx = this.xmlNodeToJSON(ud[i]);
		this._userdata[udx.name]=udx.text;
	};
	
	var evs=[];
	var xml=loader.doXPath("//event");
	
	
	for (var i=0; i < xml.length; i++) {
		evs[i]=this.xmlNodeToJSON(xml[i])
		
		evs[i].text=evs[i].text||evs[i]._tagvalue;
		evs[i].start_date=this.templates.xml_date(evs[i].start_date);
		evs[i].end_date=this.templates.xml_date(evs[i].end_date);
	}
	return evs;
}
scheduler.xmlNodeToJSON = function(node){
        var t={};
        for (var i=0; i<node.attributes.length; i++)
            t[node.attributes[i].name]=node.attributes[i].value;
        
        for (var i=0; i<node.childNodes.length; i++){
        	var child=node.childNodes[i];
            if (child.nodeType==1)
                t[child.tagName]=child.firstChild?child.firstChild.nodeValue:"";
        }
                 
        if (!t.text) t.text=node.firstChild?node.firstChild.nodeValue:"";
        
        return t;
}

scheduler.attachEvent("onXLS",function(){
	if (this.config.show_loading===true){
		var t;
		t=this.config.show_loading=document.createElement("DIV");
		t.className='dhx_loading';
		t.style.left = Math.round((this._x-128)/2)+"px";
		t.style.top = Math.round((this._y-15)/2)+"px";
		this._obj.appendChild(t);
	}
});
scheduler.attachEvent("onXLE",function(){
	var t;
	if (t=this.config.show_loading)
		if (typeof t == "object"){
		this._obj.removeChild(t);
		this.config.show_loading=true;
	}
});

scheduler.ical={
	parse:function(str){
		var data = str.match(RegExp(this.c_start+"[^\f]*"+this.c_end,""));
		if (!data.length) return;
		
		//unfolding 
		data[0]=data[0].replace(/[\r\n]+(?=[a-z \t])/g," ");
		//drop property
		data[0]=data[0].replace(/\;[^:\r\n]*/g,"");
		
		
		var incoming=[];
		var match;
		var event_r = RegExp("(?:"+this.e_start+")([^\f]*?)(?:"+this.e_end+")","g");
		while (match=event_r.exec(data)){
			var e={};
			var param;
			var param_r = /[^\r\n]+[\r\n]+/g;
			while (param=param_r.exec(match[1]))
				this.parse_param(param.toString(),e);
			if (e.uid && !e.id) e.id = e.uid; //fallback to UID, when ID is not defined
			incoming.push(e);	
		}
		return incoming;
	},
	parse_param:function(str,obj){
		var d = str.indexOf(":"); 
			if (d==-1) return;
		
		var name = str.substr(0,d).toLowerCase();
		var value = str.substr(d+1).replace(/\\\,/g,",").replace(/[\r\n]+$/,"");
		if (name=="summary")
			name="text";
		else if (name=="dtstart"){
			name = "start_date";
			value = this.parse_date(value,0,0);
		}
		else if (name=="dtend"){
			name = "end_date";
			if (obj.start_date && obj.start_date.getHours()==0)
				value = this.parse_date(value,24,00);
			else
				value = this.parse_date(value,23,59);
		}
		obj[name]=value;
	},
	parse_date:function(value,dh,dm){
		var t = value.split("T");	
		if (t[1]){
			dh=t[1].substr(0,2);
			dm=t[1].substr(2,2);
		}
		var dy = t[0].substr(0,4);
		var dn = parseInt(t[0].substr(4,2),10)-1;
		var dd = t[0].substr(6,2);
		if (scheduler.config.server_utc && !t[1]) { // if no hours/minutes were specified == full day event
			return new Date(Date.UTC(dy,dn,dd,dh,dm)) ;
		}
		return new Date(dy,dn,dd,dh,dm);
	},
	c_start:"BEGIN:VCALENDAR",
	e_start:"BEGIN:VEVENT",
	e_end:"END:VEVENT",
	c_end:"END:VCALENDAR"	
};
scheduler.form_blocks={
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
			var html="<div class='dhx_cal_ltext' style='height:"+height+";'><select style='width:552px;'>";
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
			for (var i=first; i<last; i+=this.config.time_step*1){
				var time=this.templates.time_picker(dt);
				html+="<option value='"+i+"'>"+time+"</option>";
				dt=this.date.add(dt,this.config.time_step,"minute");
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
			
			return "<div style='height:30px; padding-top:0px; font-size:inherit;' class='dhx_cal_lsection dhx_section_time'>"+html+"<span style='font-weight:normal; font-size:10pt;'> &nbsp;&ndash;&nbsp; </span>"+html+"</div>";			

		},
		set_value:function(node,value,ev){

			var s=node.getElementsByTagName("select");

			if(scheduler.config.full_day) {
				if (!node._full_day){
					node.previousSibling.innerHTML+="<div class='dhx_fullday_checkbox'><label><input type='checkbox' name='full_day' value='true'> "+scheduler.locale.labels.full_day+"&nbsp;</label></input></div>";
					node._full_day=true;
				}
				var input=node.previousSibling.getElementsByTagName("input")[0];
				var isFulldayEvent = (scheduler.date.time_part(ev.start_date)==0 && scheduler.date.time_part(ev.end_date)==0 && ev.end_date.valueOf()-ev.start_date.valueOf() < 2*24*60*60*1000);
				input.checked = isFulldayEvent;
				
				for(var k in s)
					s[k].disabled=input.checked;

				input.onclick = function(){ 
					if(input.checked) {
						var start_date = new Date(ev.start_date);
						var end_date = new Date(ev.end_date);
						
						scheduler.date.date_part(start_date);
						end_date = scheduler.date.add(start_date, 1, "day")
					} 
					for(var i in s)
						s[i].disabled=input.checked;
					
					_fill_lightbox_select(s,0,start_date||ev.start_date);
					_fill_lightbox_select(s,4,end_date||ev.end_date);
				}
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
}
scheduler.showCover=function(box){
	this.show_cover();
	if (box){
		box.style.display="block";
		var pos = getOffset(this._obj);
		box.style.top=Math.round(pos.top+(this._obj.offsetHeight-box.offsetHeight)/2)+"px";
		box.style.left=Math.round(pos.left+(this._obj.offsetWidth-box.offsetWidth)/2)+"px";	
	}
}
scheduler.showLightbox=function(id){
	if (!id) return;
	if (!this.callEvent("onBeforeLightbox",[id])) return;
	var box = this._get_lightbox();
	this.showCover(box);
	this._fill_lightbox(id,box);
	this.callEvent("onLightbox",[id]);
}
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
		block.set_value.call(this,node,ev[sns[i].map_to],ev, sns[i])
		if (sns[i].focus)
			block.focus.call(this,node);
	};
	
	scheduler._lightbox_id=id;
}
scheduler._lightbox_out=function(ev){
	var sns = this.config.lightbox.sections;	
	for (var i=0; i < sns.length; i++) {
		var node=document.getElementById(sns[i].id).nextSibling;
		var block=this.form_blocks[sns[i].type];
		var res=block.get_value.call(this,node,ev, sns[i]);
		if (sns[i].map_to!="auto")
			ev[sns[i].map_to]=res;
	}
	return ev;
}
scheduler._empty_lightbox=function(){
	var id=scheduler._lightbox_id;
	var ev=this.getEvent(id);
	var box=this._get_lightbox();
	
	this._lightbox_out(ev);
	
	ev._timed=this.is_one_day_event(ev);
	this.setEvent(ev.id,ev);
	this._edit_stop_event(ev,true)
	this.render_view_data();
}
scheduler.hide_lightbox=function(id){
	this.hideCover(this._get_lightbox());
	this._lightbox_id=null;
	this.callEvent("onAfterLightbox",[]);
}
scheduler.hideCover=function(box){
	if (box) box.style.display="none";
	this.hide_cover();
}
scheduler.hide_cover=function(){
	if (this._cover) 
		this._cover.parentNode.removeChild(this._cover);
	this._cover=null;
}
scheduler.show_cover=function(){
	this._cover=document.createElement("DIV");
	this._cover.className="dhx_cal_cover";
	document.body.appendChild(this._cover);
}
scheduler.save_lightbox=function(){
	if (this.checkEvent("onEventSave") && 						!this.callEvent("onEventSave",[this._lightbox_id,this._lightbox_out({ id: this._lightbox_id}), this._new_event]))
		return;
	this._empty_lightbox()
	this.hide_lightbox();
};
scheduler.startLightbox = function(id, box){
	this._lightbox_id=id;
	this.showCover(box);
}
scheduler.endLightbox = function(mode, box){
	this._edit_stop_event(scheduler.getEvent(this._lightbox_id),mode);
	if (mode)
		scheduler.render_view_data();
	this.hideCover(box);
};
scheduler.resetLightbox = function(){
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
					if (src.className.indexOf("dhx_custom_button_")!=-1){
						var index = src.parentNode.getAttribute("index");
						var block=scheduler.form_blocks[scheduler.config.lightbox.sections[index].type];
						var sec = src.parentNode.parentNode;
						block.button_click(index,src,sec,sec.nextSibling);	
					}
			}
	};
	this._get_lightbox().onkeypress=function(e){
		switch((e||event).keyCode){
			case scheduler.keys.edit_save:
				if ((e||event).shiftKey) return;
				scheduler.save_lightbox();
				break;
			case scheduler.keys.edit_cancel:
				scheduler.cancel_lightbox();
				break;
		}
	}
}
scheduler.setLightboxSize=function(){
	var d = this._lightbox;
	if (!d) return;
	
	var con = d.childNodes[1];
	con.style.height="0px";
	con.style.height=con.scrollHeight+"px";		
	d.style.height=con.scrollHeight+50+"px";		
	con.style.height=con.scrollHeight+"px";		 //it is incredible , how ugly IE can be 	
}

scheduler._get_lightbox=function(){
	if (!this._lightbox){
		var d=document.createElement("DIV");
		d.className="dhx_cal_light";
		if (/msie|MSIE 6/.test(navigator.userAgent))
			d.className+=" dhx_ie6";
		d.style.visibility="hidden";
		d.innerHTML=this._lightbox_template;
		document.body.insertBefore(d,document.body.firstChild);
		this._lightbox=d;
		
		var sns=this.config.lightbox.sections;
		var html="";
		for (var i=0; i < sns.length; i++) {
			var block=this.form_blocks[sns[i].type];
			if (!block) continue; //ignore incorrect blocks
			sns[i].id="area_"+this.uid();
			var button = "";
			if (sns[i].button) button = "<div style='float:right;' class='dhx_custom_button' index='"+i+"'><div class='dhx_custom_button_"+sns[i].name+"'></div><div>"+this.locale.labels["button_"+sns[i].button]+"</div></div>";
			html+="<div id='"+sns[i].id+"' class='dhx_cal_lsection'>"+button+this.locale.labels["section_"+sns[i].name]+"</div>"+block.render.call(this,sns[i]);
		};
		
	
		//localization
		var ds=d.getElementsByTagName("div");
		ds[4].innerHTML=scheduler.locale.labels.icon_save;
		ds[7].innerHTML=scheduler.locale.labels.icon_cancel;
		ds[10].innerHTML=scheduler.locale.labels.icon_delete;
		//sections
		ds[1].innerHTML=html;
		//sizes
		this.setLightboxSize();
	
		this._init_lightbox_events(this);
		d.style.display="none";
		d.style.visibility="visible";
	}
	return this._lightbox;
}
scheduler._lightbox_template="<div class='dhx_cal_ltitle'><span class='dhx_mark'>&nbsp;</span><span class='dhx_time'></span><span class='dhx_title'></span></div><div class='dhx_cal_larea'></div><div class='dhx_btn_set'><div class='dhx_save_btn'></div><div>&nbsp;</div></div><div class='dhx_btn_set'><div class='dhx_cancel_btn'></div><div>&nbsp;</div></div><div class='dhx_btn_set' style='float:right;'><div class='dhx_delete_btn'></div><div>&nbsp;</div></div>";
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