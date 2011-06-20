/*
Copyright DHTMLX LTD. http://www.dhtmlx.com
You allowed to use this component or parts of it under GPL terms
To use it on other terms or get Professional edition of the component please contact us at sales@dhtmlx.com
*/
/*
2010 September 30
*/



/* DHX DEPEND FROM FILE 'assert.js'*/


if (!window.dhtmlx) 
	dhtmlx={};

//check some rule, show message as error if rule is not correct
dhtmlx.assert = function(test, message){
	if (!test)	dhtmlx.error(message);
};
dhtmlx.assert_enabled=function(){ return false; };

//register names of event, which can be triggered by the object
dhtmlx.assert_event = function(obj, evs){
	if (!obj._event_check){
		obj._event_check = {};
		obj._event_check_size = {};
	}
		
	for (var a in evs){
		obj._event_check[a.toLowerCase()]=evs[a];
		var count=-1; for (var t in evs[a]) count++;
		obj._event_check_size[a.toLowerCase()]=count;
	}
};
dhtmlx.assert_method_info=function(obj, name, descr, rules){
	var args = [];
	for (var i=0; i < rules.length; i++) {
		args.push(rules[i][0]+" : "+rules[i][1]+"\n   "+rules[i][2].describe()+(rules[i][3]?"; optional":""));
	}
	return obj.name+"."+name+"\n"+descr+"\n Arguments:\n - "+args.join("\n - ");
};
dhtmlx.assert_method = function(obj, config){
	for (var key in config)
		dhtmlx.assert_method_process(obj, key, config[key].descr, config[key].args, (config[key].min||99), config[key].skip);
};
dhtmlx.assert_method_process = function (obj, name, descr, rules, min, skip){
	var old = obj[name];
	if (!skip)
		obj[name] = function(){
			if (arguments.length !=	rules.length && arguments.length < min) 
				dhtmlx.log("warn","Incorrect count of parameters\n"+obj[name].describe()+"\n\nExpecting "+rules.length+" but have only "+arguments.length);
			else
				for (var i=0; i<rules.length; i++)
					if (!rules[i][3] && !rules[i][2](arguments[i]))
						dhtmlx.log("warn","Incorrect method call\n"+obj[name].describe()+"\n\nActual value of "+(i+1)+" parameter: {"+(typeof arguments[i])+"} "+arguments[i]);
			
			return old.apply(this, arguments);
		};
	obj[name].describe = function(){	return dhtmlx.assert_method_info(obj, name, descr, rules);	};
};
dhtmlx.assert_event_call = function(obj, name, args){
	if (obj._event_check){
		if (!obj._event_check[name])
			dhtmlx.log("warn","Not expected event call :"+name);
		else if (dhtmlx.isNotDefined(args))
			dhtmlx.log("warn","Event without parameters :"+name);
		else if (obj._event_check_size[name] != args.length)
			dhtmlx.log("warn","Incorrect event call, expected "+obj._event_check_size[name]+" parameter(s), but have "+args.length +" parameter(s), for "+name+" event");
	}		
};
dhtmlx.assert_event_attach = function(obj, name){
	if (obj._event_check && !obj._event_check[name]) 
			dhtmlx.log("warn","Unknown event name: "+name);
};
//register names of properties, which can be used in object's configuration
dhtmlx.assert_property = function(obj, evs){
	if (!obj._settings_check)
		obj._settings_check={};
	dhtmlx.extend(obj._settings_check, evs);		
};
//check all options in collection, against list of allowed properties
dhtmlx.assert_check = function(data,coll){
	if (typeof data == "object"){
		for (var key in data){
			dhtmlx.assert_settings(key,data[key],coll);
		}
	}
};
//check if type and value of property is the same as in scheme
dhtmlx.assert_settings = function(mode,value,coll){
	coll = coll || this._settings_check;

	//if value is not in collection of defined ones
	if (coll){
		if (!coll[mode])	//not registered property
			return dhtmlx.log("warn","Unknown propery: "+mode);
			
		var descr = "";
		var error = "";
		var check = false;
		for (var i=0; i<coll[mode].length; i++){
			var rule = coll[mode][i];
			if (typeof rule == "string")
				continue;
			if (typeof rule == "function")
				check = check || rule(value);
			else if (typeof rule == "object" && typeof rule[1] == "function"){
				check = check || rule[1](value);
				if (check && rule[2])
					dhtmlx["assert_check"](value, rule[2]); //temporary fix , for sources generator
			}
			if (check) break;
		}
		if (!check )
			dhtmlx.log("warn","Invalid configuration\n"+dhtmlx.assert_info(mode,coll)+"\nActual value: {"+(typeof value)+"} "+value);
	}
};

dhtmlx.assert_info=function(name, set){ 
	var ruleset = set[name];
	var descr = "";
	var expected = [];
	for (var i=0; i<ruleset.length; i++){
		if (typeof rule == "string")
			descr = ruleset[i];
		else if (ruleset[i].describe)
			expected.push(ruleset[i].describe());
		else if (ruleset[i][1] && ruleset[i][1].describe)
			expected.push(ruleset[i][1].describe());
	}
	return "Property: "+name+", "+descr+" \nExpected value: \n - "+expected.join("\n - ");
};


if (dhtmlx.assert_enabled()){
	
	dhtmlx.assert_rule_color=function(check){
		if (typeof check != "string") return false;
		if (check.indexOf("#")!==0) return false;
		if (check.substr(1).replace(/[0-9A-F]/gi,"")!=="") return false;
		return true;
	};
	dhtmlx.assert_rule_color.describe = function(){
		return "{String} Value must start from # and contain hexadecimal code of color";
	};
	
	dhtmlx.assert_rule_template=function(check){
		if (typeof check == "function") return true;
		if (typeof check == "string") return true;
		return false;
	};
	dhtmlx.assert_rule_template.describe = function(){
		return "{Function},{String} Value must be a function which accepts data object and return text string, or a sting with optional template markers";
	};
	
	dhtmlx.assert_rule_boolean=function(check){
		if (typeof check == "boolean") return true;
		return false;
	};
	dhtmlx.assert_rule_boolean.describe = function(){
		return "{Boolean} true or false";
	};
	
	dhtmlx.assert_rule_object=function(check, sub){
		if (typeof check == "object") return true;
		return false;
	};
	dhtmlx.assert_rule_object.describe = function(){
		return "{Object} Configuration object";
	};
	
	
	dhtmlx.assert_rule_string=function(check){
		if (typeof check == "string") return true;
		return false;
	};
	dhtmlx.assert_rule_string.describe = function(){
		return "{String} Plain string";
	};
	
	
	dhtmlx.assert_rule_htmlpt=function(check){
		return !!dhtmlx.toNode(check);
	};
	dhtmlx.assert_rule_htmlpt.describe = function(){
		return "{Object},{String} HTML node or ID of HTML Node";
	};
	
	dhtmlx.assert_rule_notdocumented=function(check){
		return false;
	};
	dhtmlx.assert_rule_notdocumented.describe = function(){
		return "This options wasn't documented";
	};
	
	dhtmlx.assert_rule_key=function(obj){
		var t = function (check){
			return obj[check];
		};
		t.describe=function(){
			var opts = [];
			for(var key in obj)
				opts.push(key);
			return  "{String} can take one of next values: "+opts.join(", ");
		};
		return t;
	};
	
	dhtmlx.assert_rule_dimension=function(check){
		if (check*1 == check && !isNaN(check) && check >= 0) return true;
		return false;
	};
	dhtmlx.assert_rule_dimension.describe=function(){
		return "{Integer} value must be a positive number";
	};
	
	dhtmlx.assert_rule_number=function(check){
		if (typeof check == "number") return true;
		return false;
	};
	dhtmlx.assert_rule_number.describe=function(){
		return "{Integer} value must be a number";
	};
	
	dhtmlx.assert_rule_function=function(check){
		if (typeof check == "function") return true;
		return false;
	};
	dhtmlx.assert_rule_function.describe=function(){
		return "{Function} value must be a custom function";
	};
	
	dhtmlx.assert_rule_any=function(check){
		return true;
	};
	dhtmlx.assert_rule_any.describe=function(){
		return "Any value";
	};
	
	dhtmlx.assert_rule_mix=function(a,b){
		var t = function(check){
			if (a(check)||b(check)) return true;
			return false;
		};
		t.describe = function(){
			return a.describe();
		};
		return t;
	};

}


/* DHX DEPEND FROM FILE 'dhtmlx.js'*/


/*DHX:Depend assert.js*/

/*
	Common helpers
*/
dhtmlx.version="3.0";
dhtmlx.codebase="./";

//coding helpers

//copies methods and properties from source to the target
dhtmlx.extend = function(target, source){
	for (var method in source)
		target[method] = source[method];
		
	//applying asserts
	if (dhtmlx.assert_enabled() && source._assert){
		target._assert();
		target._assert=null;
	}
	
	dhtmlx.assert(target,"Invalid nesting target");
	dhtmlx.assert(source,"Invalid nesting source");
	//if source object has init code - call init against target
	if (source._init)	
		target._init();
				
	return target;	
};
dhtmlx.proto_extend = function(){
	var origins = arguments;
	var compilation = origins[0];
	var construct = [];
	
	for (var i=origins.length-1; i>0; i--) {
		if (typeof origins[i]== "function")
			origins[i]=origins[i].prototype;
		for (var key in origins[i]){
			if (key == "_init") 
				construct.push(origins[i][key]);
			else if (!compilation[key])
				compilation[key] = origins[i][key];
		}
	};
	
	if (origins[0]._init)
		construct.push(origins[0]._init);
	
	compilation._init = function(){
		for (var i=0; i<construct.length; i++)
			construct[i].apply(this, arguments);
	};
	compilation.base = origins[1];
	var result = function(config){
		this._init(config);
		if (this._parseSettings)
			this._parseSettings(config, this.defaults);
	};
	result.prototype = compilation;
	
	compilation = origins = null;
	return result;
};
//creates function with specified "this" pointer
dhtmlx.bind=function(functor, object){ 
	return function(){ return functor.apply(object,arguments); };  
};

//loads module from external js file
dhtmlx.require=function(module){
	if (!dhtmlx._modules[module]){
		dhtmlx.assert(dhtmlx.ajax,"load module is required");
		
		//load and exec the required module
		dhtmlx.exec( dhtmlx.ajax().sync().get(dhtmlx.codebase+module).responseText );
		dhtmlx._modules[module]=true;	
	}
};
dhtmlx._modules = {};	//hash of already loaded modules

//evaluate javascript code in the global scoope
dhtmlx.exec=function(code){
	if (window.execScript)	//special handling for IE
		window.execScript(code);
	else window.eval(code);
};

/*
	creates method in the target object which will transfer call to the source object
	if event parameter was provided , each call of method will generate onBefore and onAfter events
*/
dhtmlx.methodPush=function(object,method,event){
	return function(){
		var res = false;
		//if (!event || this.callEvent("onBefore"+event,arguments)){ //not used anymore, probably can be removed
			res=object[method].apply(object,arguments);
		//	if (event) this.callEvent("onAfter"+event,arguments);
		//}
		return res;	//result of wrapped method
	};
};
//check === undefined
dhtmlx.isNotDefined=function(a){
	return typeof a == "undefined";
};
//delay call to after-render time
dhtmlx.delay=function(method, obj, params, delay){
	setTimeout(function(){
		var ret = method.apply(obj,params);
		method = obj = params = null;
		return ret;
	},delay||1);
};

//common helpers

//generates unique ID (unique per window, nog GUID)
dhtmlx.uid = function(){
	if (!this._seed) this._seed=(new Date).valueOf();	//init seed with timestemp
	this._seed++;
	return this._seed;
};
//resolve ID as html object
dhtmlx.toNode = function(node){
	if (typeof node == "string") return document.getElementById(node);
	return node;
};
//adds extra methods for the array
dhtmlx.toArray = function(array){ 
	return dhtmlx.extend((array||[]),dhtmlx.PowerArray);
};
//resolve function name
dhtmlx.toFunctor=function(str){ 
	return (typeof(str)=="string") ? eval(str) : str; 
};

//dom helpers

//hash of attached events
dhtmlx._events = {};
//attach event to the DOM element
dhtmlx.event=function(node,event,handler,master){
	node = dhtmlx.toNode(node);
	
	var id = dhtmlx.uid();
	dhtmlx._events[id]=[node,event,handler];	//store event info, for detaching
	
	if (master) 
		handler=dhtmlx.bind(handler,master);	
		
	//use IE's of FF's way of event's attaching
	if (node.addEventListener)
		node.addEventListener(event, handler, false);
	else if (node.attachEvent)
		node.attachEvent("on"+event, handler);

	return id;	//return id of newly created event, can be used in eventRemove
};

//remove previously attached event
dhtmlx.eventRemove=function(id){
	
	if (!id) return;
	dhtmlx.assert(this._events[id],"Removing non-existing event");
		
	var ev = dhtmlx._events[id];
	//browser specific event removing
	if (ev[0].removeEventListener)
		ev[0].removeEventListener(ev[1],ev[2],false);
	else if (ev[0].detachEvent)
		ev[0].detachEvent("on"+ev[1],ev[2]);
		
	delete this._events[id];	//delete all traces
};


//debugger helpers
//anything starting from error or log will be removed during code compression

//add message in the log
dhtmlx.log = function(type,message,details){
	if (window.console && console.log){
		type=type.toLowerCase();
		if (window.console[type])
			window.console[type](message||"unknown error");
		else
			window.console.log(type +": "+message);
		if (details) 
			window.console.log(details);
	}	
};
//register rendering time from call point 
dhtmlx.log_full_time = function(name){
	dhtmlx._start_time_log = new Date();
	dhtmlx.log("Info","Timing start ["+name+"]");
	window.setTimeout(function(){
		var time = new Date();
		dhtmlx.log("Info","Timing end ["+name+"]:"+(time.valueOf()-dhtmlx._start_time_log.valueOf())/1000+"s");
	},1);
};
//register execution time from call point
dhtmlx.log_time = function(name){
	var fname = "_start_time_log"+name;
	if (!dhtmlx[fname]){
		dhtmlx[fname] = new Date();
		dhtmlx.log("Info","Timing start ["+name+"]");
	} else {
		var time = new Date();
		dhtmlx.log("Info","Timing end ["+name+"]:"+(time.valueOf()-dhtmlx[fname].valueOf())/1000+"s");
		dhtmlx[fname] = null;
	}
};
//log message with type=error
dhtmlx.error = function(message,details){
	dhtmlx.log("error",message,details);
};
//event system
dhtmlx.EventSystem={
	_init:function(){
		this._events = {};		//hash of event handlers, name => handler
		this._handlers = {};	//hash of event handlers, ID => handler
		this._map = {};
	},
	//temporary block event triggering
	block : function(){
		this._events._block = true;
	},
	//re-enable event triggering
	unblock : function(){
		this._events._block = false;
	},
	mapEvent:function(map){
		dhtmlx.extend(this._map, map);
	},
	//trigger event
	callEvent:function(type,params){
		if (this._events._block) return true;
		
		type = type.toLowerCase();
		dhtmlx.assert_event_call(this, type, params);
		
		var event_stack =this._events[type.toLowerCase()];	//all events for provided name
		var return_value = true;

		if (dhtmlx.debug)	//can slowdown a lot
			dhtmlx.log("info","["+this.name+"] event:"+type,params);
		
		if (event_stack)
			for(var i=0; i<event_stack.length; i++)
				/*
					Call events one by one
					If any event return false - result of whole event will be false
					Handlers which are not returning anything - counted as positive
				*/
				if (event_stack[i].apply(this,(params||[]))===false) return_value=false;
				
		if (this._map[type] && !this._map[type].callEvent(type,params))
			return_value =	false;
			
		return return_value;
	},
	//assign handler for some named event
	attachEvent:function(type,functor,id){
		type=type.toLowerCase();
		dhtmlx.assert_event_attach(this, type);
		
		id=id||dhtmlx.uid(); //ID can be used for detachEvent
		functor = dhtmlx.toFunctor(functor);	//functor can be a name of method

		var event_stack=this._events[type]||dhtmlx.toArray();
		//save new event handler
		event_stack.push(functor);
		this._events[type]=event_stack;
		this._handlers[id]={ f:functor,t:type };
		
		return id;
	},
	//remove event handler
	detachEvent:function(id){
		var type=this._handlers[id].t;
		var functor=this._handlers[id].f;
		
		//remove from all collections
		var event_stack=this._events[type];
		event_stack.remove(functor);
		delete this._handlers[id];
	} 
};

//array helper
//can be used by dhtmlx.toArray()
dhtmlx.PowerArray={
	//remove element at specified position
	removeAt:function(pos,len){
		if (pos>=0) this.splice(pos,(len||1));
	},
	//find element in collection and remove it 
	remove:function(value){
		this.removeAt(this.find(value));
	},	
	//add element to collection at specific position
	insertAt:function(data,pos){
		if (!pos && pos!==0) 	//add to the end by default
			this.push(data);
		else {	
			var b = this.splice(pos,(this.length-pos));
  			this[pos] = data;
  			this.push.apply(this,b); //reconstruct array without loosing this pointer
  		}
  	},  	
  	//return index of element, -1 if it doesn't exists
  	find:function(data){ 
  		for (i=0; i<this.length; i++) 
  			if (data==this[i]) return i; 	
  		return -1; 
  	},
  	//execute some method for each element of array
  	each:function(functor,master){
		for (var i=0; i < this.length; i++)
			functor.call((master||this),this[i]);
	},
	//create new array from source, by using results of functor 
	map:function(functor,master){
		for (var i=0; i < this.length; i++)
			this[i]=functor.call((master||this),this[i]);
		return this;
	}
};

dhtmlx.env = {};

//environment detection
if (navigator.userAgent.indexOf('Opera') != -1)
	dhtmlx._isOpera=true;
else{
	//very rough detection, but it is enough for current goals
	dhtmlx._isIE=!!document.all;
	dhtmlx._isFF=!document.all;
	dhtmlx._isWebKit=(navigator.userAgent.indexOf("KHTML")!=-1);
	if (navigator.appVersion.indexOf("MSIE 8.0")!= -1 && document.compatMode != "BackCompat") 
		dhtmlx._isIE=8;
}

dhtmlx.env = {};

// dhtmlx.env.transform 
// dhtmlx.env.transition
(function(){
	dhtmlx.env.transform = false;
	dhtmlx.env.transition = false;
	var options = {};
	options.names = ['transform', 'transition'];
	options.transform = ['transform', 'WebkitTransform', 'MozTransform', 'oTransform'];
	options.transition = ['transition', 'WebkitTransition', 'MozTransition', 'oTransition'];
	
	var d = document.createElement("DIV");
	var property;
	for(var i=0; i<options.names.length; i++) {
		while (p = options[options.names[i]].pop()) {
			if(typeof d.style[p] != 'undefined')
				dhtmlx.env[options.names[i]] = true;
		}
	}
})();
dhtmlx.env.transform_prefix = (function(){
		var prefix;
		if(dhtmlx._isOpera)
			prefix = '-o-';
		else {
			prefix = ''; // default option
			if(dhtmlx._isFF) 
				prefix = '-moz-';
			if(dhtmlx._isWebKit) 
					prefix = '-webkit-';
		}
		return prefix;
})();
dhtmlx.env.svg = (function(){
		return document.implementation.hasFeature("http://www.w3.org/TR/SVG11/feature#BasicStructure", "1.1");
})();

//store maximum used z-index
dhtmlx.zIndex={ drag : 10000 };

//html helpers
dhtmlx.html={
	create:function(name,attrs,html){
		attrs = attrs || {};
		var node = document.createElement(name);
		for (var attr_name in attrs)
			node.setAttribute(attr_name, attrs[attr_name]);
		if (attrs.style)
			node.style.cssText = attrs.style;
		if (attrs["class"])
			node.className = attrs["class"];
		if (html)
			node.innerHTML=html;
		return node;
	},
	//return node value, different logic for different html elements
	getValue:function(node){
		node = dhtmlx.toNode(node);
		if (!node) return "";
		return dhtmlx.isNotDefined(node.value)?node.innerHTML:node.value;
	},
	//remove html node, can process an array of nodes at once
	remove:function(node){
		if (node instanceof Array)
			for (var i=0; i < node.length; i++)
				this.remove(node[i]);
		else
			if (node && node.parentNode)
				node.parentNode.removeChild(node);
	},
	//insert new node before sibling, or at the end if sibling doesn't exist
	insertBefore: function(node,before,rescue){
		if (!node) return;
		if (before)
			before.parentNode.insertBefore(node, before);
		else
			rescue.appendChild(node);
	},
	//return custom ID from html element 
	//will check all parents starting from event's target
	locate:function(e,id){
		e=e||event;
		var trg=e.target||e.srcElement;
		while (trg){
			if (trg.getAttribute){	//text nodes has not getAttribute
				var test = trg.getAttribute(id);
				if (test) return test;
			}
			trg=trg.parentNode;
		}	
		return null;
	},
	//returns position of html element on the page
	offset:function(elem) {
		if (elem.getBoundingClientRect) { //HTML5 method
			var box = elem.getBoundingClientRect();
			var body = document.body;
			var docElem = document.documentElement;
			var scrollTop = window.pageYOffset || docElem.scrollTop || body.scrollTop;
			var scrollLeft = window.pageXOffset || docElem.scrollLeft || body.scrollLeft;
			var clientTop = docElem.clientTop || body.clientTop || 0;
			var clientLeft = docElem.clientLeft || body.clientLeft || 0;
			var top  = box.top +  scrollTop - clientTop;
			var left = box.left + scrollLeft - clientLeft;
			return { y: Math.round(top), x: Math.round(left) };
		} else { //fallback to naive approach
			var top=0, left=0;
			while(elem) {
				top = top + parseInt(elem.offsetTop,10);
				left = left + parseInt(elem.offsetLeft,10);
				elem = elem.offsetParent;
			}
			return {y: top, x: left};
		}
	},
	//returns position of event
	pos:function(ev){
		ev = ev || event;
        if(ev.pageX || ev.pageY)	//FF, KHTML
            return {x:ev.pageX, y:ev.pageY};
        //IE
        var d  =  ((dhtmlx._isIE)&&(document.compatMode != "BackCompat"))?document.documentElement:document.body;
        return {
                x:ev.clientX + d.scrollLeft - d.clientLeft,
                y:ev.clientY + d.scrollTop  - d.clientTop
        };
	},
	//prevent event action
	preventEvent:function(e){
		if (e && e.preventDefault) e.preventDefault();
		dhtmlx.html.stopEvent(e);
	},
	//stop event bubbling
	stopEvent:function(e){
		(e||event).cancelBubble=true;
		return false;
	},
	//add css class to the node
	addCss:function(node,name){
        node.className+=" "+name;
    },
    //remove css class from the node
    removeCss:function(node,name){
        node.className=node.className.replace(RegExp(name,"g"),"");
    }
};

//autodetect codebase folder
(function(){
	var temp = document.getElementsByTagName("SCRIPT");	//current script, most probably
	dhtmlx.assert(temp.length,"Can't locate codebase");
	if (temp.length){
		//full path to script
		temp = (temp[temp.length-1].getAttribute("src")||"").split("/");
		//get folder name
		temp.splice(temp.length-1, 1);
		dhtmlx.codebase = temp.slice(0, temp.length).join("/")+"/";
	}
})();

dhtmlx.ui={};


/* DHX DEPEND FROM FILE 'destructor.js'*/


/*
	Behavior:Destruction
	
	@export
		destructor
*/

/*DHX:Depend dhtmlx.js*/

dhtmlx.Destruction = {
	_init:function(){
		//register self in global list of destructors
		dhtmlx.destructors.push(this);
	},
	//will be called automatically on unload, can be called manually
	//simplifies job of GC
	destructor:function(){
		this.destructor=function(){}; //destructor can be called only once
		
		//html collection
		this._htmlmap  = null;
		this._htmlrows = null;
		
		//temp html element, used by toHTML
		if (this._html)
			document.body.appendChild(this._html);	//need to attach, for IE's GC

		this._html = null;
		if (this._obj) {
			this._obj.innerHTML="";
			this._obj._htmlmap = null;
		}
		this._obj = this._dataobj=null;
		this.data = null;
		this._events = this._handlers = {};
	}
};
//global list of destructors
dhtmlx.destructors = [];
dhtmlx.event(window,"unload",function(){
	//call all registered destructors
	for (var i=0; i<dhtmlx.destructors.length; i++)
		dhtmlx.destructors[i].destructor();
	dhtmlx.destructors = [];
	
	//detach all known DOM events
	for (var a in dhtmlx._events){
		var ev = dhtmlx._events[a];
		if (ev[0].removeEventListener)
			ev[0].removeEventListener(ev[1],ev[2],false);
		else if (ev[0].detachEvent)
			ev[0].detachEvent("on"+ev[1],ev[2]);
		delete dhtmlx._events[a];
	}
});


/* DHX DEPEND FROM FILE 'math.js'*/


dhtmlx.math = {};
dhtmlx.math._toHex=["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"];
dhtmlx.math.toHex = function(number, length){
	number=parseInt(number,10);
	str = "";
		while (number>0){
			str=this._toHex[number%16]+str;
			number=Math.floor(number/16);
		}
		while (str.length <length)
			str = "0"+str;
	return str;
};





/* DHX DEPEND FROM FILE 'map.js'*/


/*DHX:Depend dhtmlx.js*/
	
dhtmlx.ui.Map = function(key){
	this.name = "Map";
	this._id = "map_"+dhtmlx.uid();
	this._key = key;
	this._map = [];
};
dhtmlx.ui.Map.prototype = {
	addRect: function(id,points,userdata) {
		this._createMapArea(id,"RECT",points,userdata);
	},
	addPoly: function(id,points) {
		this._createMapArea(id,"POLY",points);
	},
	_createMapArea:function(id,shape,coords,userdata){
		var extra_data = "";
		if(arguments.length==4) 
			extra_data = "userdata='"+userdata+"'";
		this._map.push("<area "+this._key+"='"+id+"' shape='"+shape+"' coords='"+coords.join()+"' "+extra_data+"></area>");
	},
	addSector:function(id,alpha0,alpha1,x,y,R,ky){
		var points = [];
		points.push(x);
		points.push(Math.floor(y*ky)); 
		for(var i = alpha0; i < alpha1; i+=Math.PI/18){
			points.push(Math.floor(x+R*Math.cos(i)));
			points.push(Math.floor((y+R*Math.sin(i))*ky));
		}
		points.push(Math.floor(x+R*Math.cos(alpha1)));
		points.push(Math.floor((y+R*Math.sin(alpha1))*ky));
		points.push(x);
		points.push(Math.floor(y*ky)); 
		
		return this.addPoly(id,points);
	},
	render:function(obj){
		var d = dhtmlx.html.create("DIV");
		d.style.cssText="position:absolute; width:100%; height:100%; top:0px; left:0px;";
		obj.appendChild(d);
		var src = dhtmlx._isIE?"":"src='data:image/gif;base64,R0lGODlhEgASAIAAAP///////yH5BAUUAAEALAAAAAASABIAAAIPjI+py+0Po5y02ouz3pwXADs='";
		d.innerHTML="<map id='"+this._id+"' name='"+this._id+"'>"+this._map.join("\n")+"</map><img "+src+" class='dhx_map_img' usemap='#"+this._id+"'>";
		
		obj._htmlmap = d; //for clearing routine
		
		this._map = [];
	}
};


/* DHX DEPEND FROM FILE 'ext/chart/chart_base.js'*/


/*DHX:Depend map.js*/
dhtmlx.chart = {};


/* DHX DEPEND FROM FILE 'ext/chart/chart_area.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
dhtmlx.chart.area = {
	/**
	*   renders an area chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: width - the width of the container
	*   @param: height - the height of the container
	*   @param: sIndex - index of drawing chart
	*/
	pvt_render_area:function(ctx, data, point0, point1, sIndex, map){
				
	    var params = this._calculateParametersOfLineChart(ctx,data,point0,point1,sIndex);
			
		/*the value that defines the map area position*/
		var areaPos = Math.floor(params.cellWidth/2);
	
		/*drawing all items*/
		if (data.length) {
			
			ctx.globalAlpha = this._settings.alpha.call(this,data[0]);
			ctx.fillStyle = this._settings.color.call(this,data[0]);
		  
			/*the position of the first item*/
			var y0 = this._getYPointOfLineChart(data[0],point0,point1,params);
			var x0 = (this._settings.offset?point0.x+params.cellWidth*0.5:point0.x);
			ctx.beginPath();
			ctx.moveTo(x0,point1.y);
			ctx.lineTo(x0,y0);
			
			/*creates map area*/
			map.addRect(data[0].id,[x0-areaPos,y0-areaPos,x0+areaPos,y0+areaPos]);
			/*item label*/
			if(!this._settings.yAxis)
		    	this.renderTextAt(false, (!this._settings.offset?false:true), x0, y0-this._settings.labelOffset, this._settings.label(data[0]));
				
			/*drawing the previous item and the line between to items*/
			for(var i=1; i < data.length;i ++){
				/*horizontal positions of the previous and current items (0.5 - the fix for line width)*/
				var xi = x0+ Math.floor(params.cellWidth*i) - 0.5;
				var yi = this._getYPointOfLineChart(data[i],point0,point1,params);
				ctx.lineTo(xi,yi);
				/*creates map area*/
				map.addRect(data[i].id,[xi-areaPos,yi-areaPos,xi+areaPos,yi+areaPos]);
				/*item label*/
				if(!this._settings.yAxis)
					this.renderTextAt(false, (!this._settings.offset&&i==(data.length-1)?"left":"center"), xi, yi-this._settings.labelOffset, this._settings.label(data[i]));
			}
			ctx.lineTo(x0+Math.floor(params.cellWidth*[data.length-1]),point1.y);
			ctx.lineTo(x0,point1.y);
			ctx.fill();
		}
	}
};
dhtmlx.chart.stackedArea ={
	/**
	*   renders an area chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: width - the width of the container
	*   @param: height - the height of the container
	*   @param: sIndex - index of drawing chart
	*/
	pvt_render_stackedArea:function(ctx, data, point0, point1, sIndex, map){
				
	  	var params = this._calculateParametersOfLineChart(ctx,data,point0,point1,sIndex);
			
		/*the value that defines the map area position*/
		var areaPos = Math.floor(params.cellWidth/2);
	  
	    var y1 = [];
	
		/*drawing all items*/
		if (data.length) {
			
			ctx.globalAlpha = this._settings.alpha.call(this,data[0]);
			ctx.fillStyle = this._settings.color.call(this,data[0]);

		   /*for the 2nd, 3rd, etc. series*/
		    var y01 = (sIndex?data[0].$startY:point1.y);
		   
		   	/*the position of the first item*/
			var x0 = (this._settings.offset?point0.x+params.cellWidth*0.5:point0.x);
		  	var y02 = this._getYPointOfLineChart(data[0],point0,point1,params)-(sIndex?(point1.y-y01):0);
			
			y1[0] = y02;
				
			ctx.beginPath();
			ctx.moveTo(x0,y01);
			ctx.lineTo(x0,y02);
			
			/*creates map area*/
			map.addRect(data[0].id,[x0-areaPos,y02-areaPos,x0+areaPos,y02+areaPos]);
			/*item label*/
			if(!this._settings.yAxis)
		    	this.renderTextAt(false, true, x0, y02-this._settings.labelOffset, this._settings.label(data[0]));
			
			/*drawing the previous item and the line between to items*/
			for(var i=1; i < data.length;i ++){
				/*horizontal positions of the previous and current items (0.5 - the fix for line width)*/
				var xi = x0+ Math.floor(params.cellWidth*i) - 0.5;
				var yi2 = this._getYPointOfLineChart(data[i],point0,point1,params)-(sIndex?(point1.y-data[i].$startY):0);
				
				y1[i] = yi2;
				
				ctx.lineTo(xi,yi2);
				/*creates map area*/
				map.addRect(data[i].id,[xi-areaPos,yi2-areaPos,xi+areaPos,yi2+areaPos]);
				/*item label*/
				if(!this._settings.yAxis)
					this.renderTextAt(false, true, xi, yi2-this._settings.labelOffset, this._settings.label(data[i]));
			}
			ctx.lineTo(x0+Math.floor(params.cellWidth*[data.length-1]),y01);
			/*drawing lines of the lower part*/
			if(sIndex){
				for(var i=data.length-1; i >=0 ;i--){
					var xi = x0+ Math.floor(params.cellWidth*i) - 0.5;
					var yi1 = data[i].$startY;
					ctx.lineTo(xi,yi1);
				}
			}
			else ctx.lineTo(x0+ Math.floor(params.cellWidth*(length-1)) - 0.5,y01);
			ctx.lineTo(x0,y01);
			ctx.fill();
			for(var i=0; i < data.length;i ++){
				data[i].$startY = y1[i];
			}
		}
	}
};



/* DHX DEPEND FROM FILE 'ext/chart/chart_spline.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
dhtmlx.chart.spline = {
	/**
	*   renders a spline chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: width - the width of the container
	*   @param: height - the height of the container
	*   @param: sIndex - index of drawing chart
	*/
	pvt_render_spline:function(ctx, data, point0, point1, sIndex, map){
			
		var params = this._calculateParametersOfLineChart(ctx,data,point0,point1,sIndex);
		
		/*the value that defines the map area position*/
		var areaPos = Math.floor(params.cellWidth/2);
		
		/*array of all points*/
		var items = [];
		
		/*drawing all items*/
		if (data.length) {
		   
			/*getting all points*/
			var x0 = (this._settings.offset?point0.x+params.cellWidth*0.5:point0.x);
			for(var i=0; i < data.length;i ++){
				var x = ((!i)?x0:Math.floor(params.cellWidth*i) - 0.5 + x0);
			    var y = this._getYPointOfLineChart(data[i],point0,point1,params);		
				items.push({x:x,y:y});
			}
			var sparam = this._getSplineParameters(items);
			
			for(var i =0; i< items.length-1; i++){
				var x1 = items[i].x;
				var y1 = items[i].y;
				var x2 = items[i+1].x;
				var y2 = items[i+1].y;
				
				
				for(var j = x1; j < x2; j++)
					this._drawLine(ctx,j,this._getSplineYPoint(j,x1,i,sparam.a,sparam.b,sparam.c,sparam.d),j+1,this._getSplineYPoint(j+1,x1,i,sparam.a,sparam.b,sparam.c,sparam.d),this._settings.line.color(data[i]),this._settings.line.width);
				this._drawLine(ctx,x2-1,this._getSplineYPoint(j,x1,i,sparam.a,sparam.b,sparam.c,sparam.d),x2,y2,this._settings.line.color(data[i]),this._settings.line.width);
				this._drawItemOfLineChart(ctx,x1,y1,data[i],this._settings.label(data[i]));
			}
			this._drawItemOfLineChart(ctx,x2,y2,data[i],this._settings.label(data[i]));
		}
	},
	/*gets spline parameter*/
	_getSplineParameters:function(points){
		var h,u,v,s,a,b,c,d,n;
		h = [];	m = [];
		n = points.length;
		
		for(var i =0; i<n-1;i++){
			h[i] = points[i+1].x - points[i].x;
			m[i] = (points[i+1].y - points[i].y)/h[i];
		}
		u = [];	v = [];
		u[0] = 0;
		u[1] = 2*(h[0] + h[1]);
		v[0] = 0;
		v[1] = 6*(m[1] - m[0]);
		for(var i =2; i < n-1; i++){
			u[i] = 2*(h[i-1]+h[i]) - h[i-1]*h[i-1]/u[i-1];
	    	v[i] = 6*(m[i]-m[i-1]) - h[i-1]*v[i-1]/u[i-1];
		}
		
		s = [];
		s[n-1] = s[0] = 0;
		for(var i = n -2; i>=1; i--)
	   		s[i] = (v[i] - h[i]*s[i+1])/u[i];
	
        a = []; b = []; c = [];	d = []; 
		
		for(var i =0; i<n-1;i++){
			a[i] = points[i].y;
			b[i] = - h[i]*s[i+1]/6 - h[i]*s[i]/3 + (points[i+1].y-points[i].y)/h[i];
			c[i] = s[i]/2;
			d[i] = (s[i+1] - s[i])/(6*h[i]);
		}
		return {a:a,b:b,c:c,d:d};
	},
	/*returns the y position of the spline point */
	_getSplineYPoint:function(x,xi,i,a,b,c,d){
		return a[i] + (x - xi)*(b[i] + (x-xi)*(c[i]+(x-xi)*d[i])); 
	}
};


/* DHX DEPEND FROM FILE 'ext/chart/chart_barh.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
dhtmlx.chart.barH = {
	/**
	*   renders a bar chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: x - the width of the container
	*   @param: y - the height of the container
	*   @param: sIndex - index of drawing chart
	*/
	pvt_render_barH:function(ctx, data, point0, point1, sIndex, map){
	     var maxValue,minValue;
		/*necessary if maxValue - minValue < 0*/
		var valueFactor;
		/*maxValue - minValue*/
		var relValue;
		
		var total_width = point1.x-point0.x;
		
		var yax = !!this._settings.yAxis;
		var xax = !!this._settings.xAxis;
		
		var limits = this._getLimits("h");
		maxValue = limits.max;
		minValue = limits.min;
		
		/*an available width for one bar*/
		var cellWidth = Math.floor((point1.y-point0.y)/data.length);
		
		/*draws x and y scales*/
		if(!sIndex)
			this._drawHScales(ctx,data,point0, point1,minValue,maxValue,cellWidth);
		
		/*necessary for automatic scale*/
		if(yax){
		    maxValue = parseFloat(this._settings.xAxis.end);
			minValue = parseFloat(this._settings.xAxis.start);      
		}
		
		/*unit calculation (bar_height = value*unit)*/
		var relativeValues = this._getRelativeValue(minValue,maxValue);
		relValue = relativeValues[0];
		valueFactor = relativeValues[1];
		
		var unit = (relValue?total_width/relValue:10);
		if(!yax){
			/*defines start value for better representation of small values*/
			var startValue = 10;
			unit = (relValue?(total_width-startValue)/relValue:10);
		}
		
		
		/*a real bar width */
		var barWidth = parseInt(this._settings.width,10);
		if((barWidth*this._series.length+4)>cellWidth) barWidth = cellWidth/this._series.length-4;
		/*the half of distance between bars*/
		var barOffset = Math.floor((cellWidth - barWidth*this._series.length)/2);
		/*the radius of rounding in the top part of each bar*/
		var radius = (typeof this._settings.radius!="undefined"?parseInt(this._settings.radius,10):Math.round(barWidth/5));
		
		var inner_gradient = false;
		var gradient = this._settings.gradient;
	
		if (gradient&&typeof(gradient) != "function"){
			inner_gradient = gradient;
			gradient = false;
		} else if (gradient){
			gradient = ctx.createLinearGradient(point0.x,point0.y,point1.x,point0.y);
			this._settings.gradient(gradient);
		}
		var scaleY = 0;
		/*draws a black line if the horizontal scale isn't defined*/
		if(!yax){
			this._drawLine(ctx,point0.x-0.5,point0.y,point0.x-0.5,point1.y,"#000000",1); //hardcoded color!
		}
		
		
		
		for(var i=0; i < data.length;i ++){
			
			
			var value =  parseFloat(this._settings.value(data[i]));
			if(value>maxValue) value = maxValue;
			value -= minValue;
			value *= valueFactor;
			
			/*start point (bottom left)*/
			var x0 = point0.x;
			var y0 = point0.y+ barOffset + i*cellWidth+(barWidth+1)*sIndex;
			
			if(value<0||(this._settings.yAxis&&value===0)){
				this.renderTextAt(true, true, x0+Math.floor(barWidth/2),y0,this._settings.label(data[i]));
				continue;
			}
			
			/*takes start value into consideration*/
			if(!yax) value += startValue/unit;
			var color = gradient||this._settings.color.call(this,data[i]);
			
			/*drawing the gradient border of a bar*/
			if(this._settings.border){
				ctx.beginPath();
				ctx.fillStyle = color;
				this._setBarHPoints(ctx,x0,y0,barWidth,radius,unit,value,0);
				ctx.lineTo(x0,0);
				ctx.fill();

				ctx.fillStyle = "#000000";
				ctx.globalAlpha = 0.37;
				ctx.beginPath();
				this._setBarHPoints(ctx,x0,y0,barWidth,radius,unit,value,0);
				ctx.fill();
			}
			
			/*drawing bar body*/
			ctx.globalAlpha = this._settings.alpha.call(this,data[i]);
			ctx.fillStyle = (gradient||this._settings.color.call(this,data[i]));
			ctx.beginPath();
			var points = this._setBarHPoints(ctx,x0,y0,barWidth,radius,unit,value,(this._settings.border?1:0));
			if (gradient&&!inner_gradient) ctx.lineTo(point0.x+total_width,y0+(this._settings.border?1:0)); //fix gradient sphreading
   			ctx.fill();
			ctx.globalAlpha = 1;
			
			if (inner_gradient!=false){
				var gradParam = this._setBarGradient(ctx,point0.x,y0+barWidth,point0.x+unit*value+2,y0,inner_gradient,color,"x");
				ctx.fillStyle = gradParam.gradient;
				ctx.beginPath();
				var points = this._setBarHPoints(ctx,x0,y0+gradParam.offset,barWidth-gradParam.offset*2,radius,unit,value,gradParam.offset);
				ctx.fill();
				ctx.globalAlpha = 1;
			}
			
			
			/*sets a bar label*/
			this.renderTextAt("middle",false,points[0]+3, parseInt(y0+(points[1]-y0)/2,10), this._settings.label(data[i]));
			/*defines a map area for a bar*/
			map.addRect(data[i].id,[x0,y0,points[0],points[1]],sIndex);
		}
	},
	/**
	*   sets points for bar and returns the position of the bottom right point
	*   @param: ctx - canvas object
	*   @param: x0 - the x position of start point
	*   @param: y0 - the y position of start point
	*   @param: barWidth - bar width 
	*   @param: radius - the rounding radius of the top
	*   @param: unit - the value defines the correspondence between item value and bar height
	*   @param: value - item value
	*   @param: offset - the offset from expected bar edge (necessary for drawing border)
	*/
	_setBarHPoints:function(ctx,x0,y0,barWidth,radius,unit,value,offset){
		/*correction for displaing small values (when rounding radius is bigger than bar height)*/
		var angle_corr = 0;
		if(radius>unit*value){
			var sinA = (radius-unit*value)/radius;
			angle_corr = -Math.asin(sinA)+Math.PI/2;
		}
		/*start*/
		ctx.moveTo(x0,y0+offset);
		/*start of left rounding*/
		var x1 = x0 + unit*value - radius - (radius?0:offset);
		if(radius<unit*value)
			ctx.lineTo(x1,y0+offset);
   		/*left rounding*/
		var y2 = y0 + radius;
		if (radius)
			ctx.arc(x1,y2,radius-offset,-Math.PI/2+angle_corr,0,false);
   		/*start of right rounding*/
		var y3 = y0 + barWidth - radius - (radius?0:offset);
		var x3 = x1 + radius - (radius?offset:0);
		ctx.lineTo(x3,y3);
		/*right rounding*/
		var x4 = x1;
		if (radius)
			ctx.arc(x4,y3,radius-offset,0,Math.PI/2-angle_corr,false);
   		/*bottom right point*/
		var y5 = y0 + barWidth-offset;
        ctx.lineTo(x0,y5);
		/*line to the start point*/
   		ctx.lineTo(x0,y0+offset);
   	//	ctx.lineTo(x0,0); //IE fix!
		return [x3,y5];
	},
	 _drawHScales:function(ctx,data,point0,point1,start,end,cellWidth){
	    this._drawHXAxis(ctx,data,point0,point1,start,end);
		this._drawHYAxis(ctx,data,point0,point1,cellWidth);
	},
	_drawHYAxis:function(ctx,data,point0,point1,cellWidth){
		if (!this._settings.yAxis) return;
		
		var x0 = point0.x-0.5;
		var y0 = point1.y+0.5;
		var y1 = point0.y;
			
		this._drawLine(ctx,x0,y0,x0,y1,this._settings.yAxis.color,1);
		
		for(var i=0; i < data.length;i ++){
				
			/*scale labels*/
			this.renderTextAt("middle",0,0,y1+cellWidth/2+i*cellWidth,
				this._settings.yAxis.template(data[i]),
				"dhx_axis_item_y",point0.x-5
			);
		}
		this._setYAxisTitle(point0,point1);
	},
	_drawHXAxis:function(ctx,data,point0,point1,start,end){
		var step;
		var scaleParam= {};
		var axis = this._settings.xAxis;
		if (!axis) return;
		
		var y0 = point1.y+0.5;
		var x0 = point0.x-0.5;
		var x1 = point1.x-0.5;
		
		this._drawLine(ctx,x0,y0,x1,y0,axis.color,1);
		
		if(axis.step)
		     step = parseFloat(axis.step);
		
		if(typeof axis.step =="undefined"||typeof axis.start=="undefined"||typeof axis.end =="undefined"){
			scaleParam = this._calculateScale(start,end);
			start = scaleParam.start;
			end = scaleParam.end;
			step = scaleParam.step;
			this._settings.xAxis.end = end;
			this._settings.xAxis.start = start;
			this._settings.xAxis.step = step;
		};
		
		if(step===0) return;
		var stepHeight = (x1-x0)*step/(end-start);
		var c = 0;
		for(var i = start; i<=end; i += step){
			if(scaleParam.fixNum)  i = parseFloat((new Number(i)).toFixed(scaleParam.fixNum));
			var xi = Math.floor(x0+c*stepHeight)+ 0.5;/*canvas line fix*/
			if(i!=start &&axis.lines)
				this._drawLine(ctx,xi,y0,xi,point0.y,this._settings.xAxis.color,0.2);	
			this.renderTextAt(false, true,xi,y0+2,axis.template(i.toString()),"dhx_axis_item_x");
			c++;
		};
		this.renderTextAt(true, false, x0,point1.y+this._settings.padding.bottom-3,
			this._settings.xAxis.title,
			"dhx_axis_title_x",
			point1.x - point0.x
		);
		/*the right border in lines in scale are enabled*/
		if (!axis.lines) return;
			this._drawLine(ctx,x0,point0.y-0.5,x1,point0.y-0.5,this._settings.xAxis.color,0.2);
	}
	
};



/* DHX DEPEND FROM FILE 'ext/chart/chart_stackedbarh.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
/*DHX:Depend ext/chart/chart_barh.js*/

dhtmlx.assert(dhtmlx.chart.barH);
dhtmlx.chart.stackedBarH = {
/**
	*   renders a bar chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: x - the width of the container
	*   @param: y - the height of the container
	*   @param: sIndex - index of drawing chart
	*   @param: map - map object
	*/
	pvt_render_stackedBarH:function(ctx, data, point0, point1, sIndex, map){
	   var maxValue,minValue;
		/*necessary if maxValue - minValue < 0*/
		var valueFactor;
		/*maxValue - minValue*/
		var relValue;
		
		var total_width = point1.x-point0.x;
		
		var yax = !!this._settings.yAxis;
		var xax = !!this._settings.xAxis;
		
		var limits = this._getStackedLimits(data);
		maxValue = limits.max;
		minValue = limits.min;
		
		/*an available width for one bar*/
		var cellWidth = Math.floor((point1.y-point0.y)/data.length);
	
		/*draws x and y scales*/
		if(!sIndex)
			this._drawHScales(ctx,data,point0, point1,minValue,maxValue,cellWidth);
		
		/*necessary for automatic scale*/
		if(yax){
		    maxValue = parseFloat(this._settings.xAxis.end);
			minValue = parseFloat(this._settings.xAxis.start);      
		}
		
		/*unit calculation (bar_height = value*unit)*/
		var relativeValues = this._getRelativeValue(minValue,maxValue);
		relValue = relativeValues[0];
		valueFactor = relativeValues[1];
		
		var unit = (relValue?total_width/relValue:10);
		if(!yax){
			/*defines start value for better representation of small values*/
			var startValue = 10;
			unit = (relValue?(total_width-startValue)/relValue:10);
		}
		
		/*a real bar width */
		var barWidth = parseInt(this._settings.width,10);
		if((barWidth+4)>cellWidth) barWidth = cellWidth-4;
		/*the half of distance between bars*/
		var barOffset = Math.floor((cellWidth - barWidth)/2);
		/*the radius of rounding in the top part of each bar*/
		var radius = 0;
		
		var inner_gradient = false;
		var gradient = this._settings.gradient;
	
		var inner_gradient = false;
		var gradient = this._settings.gradient;
		if (gradient){
			inner_gradient = true;
		} 
		var scaleY = 0;
		/*draws a black line if the horizontal scale isn't defined*/
		if(!yax){
			this._drawLine(ctx,point0.x-0.5,point0.y,point0.x-0.5,point1.y,"#000000",1); //hardcoded color!
		}
		
		for(var i=0; i < data.length;i ++){
			
			if(!sIndex) 
			   data[i].$startX = point0.x;
			
			var value =  parseFloat(this._settings.value(data[i]));
			if(value>maxValue) value = maxValue;
			value -= minValue;
			value *= valueFactor;
			
			/*start point (bottom left)*/
			var x0 = point0.x;
			var y0 = point0.y+ barOffset + i*cellWidth;
			
			/*for the 2nd, 3rd, etc. series*/
			if(sIndex)
			    x0 = data[i].$startX || x0;
			
			if(value<0||(this._settings.yAxis&&value===0)){
				this.renderTextAt(true, true, x0+Math.floor(barWidth/2),y0,this._settings.label(data[i]));
				continue;
			}
			
			/*takes start value into consideration*/
			if(!yax) value += startValue/unit;
			var color = this._settings.color.call(this,data[i]);
			
			/*drawing the gradient border of a bar*/
			if(this._settings.border){
				ctx.beginPath();
				ctx.fillStyle = color;
				this._setBarHPoints(ctx,x0,y0,barWidth,radius,unit,value,0);
				ctx.lineTo(x0,0);
				ctx.fill();

				ctx.fillStyle = "#000000";
				ctx.globalAlpha = 0.37;
				ctx.beginPath();
				this._setBarHPoints(ctx,x0,y0,barWidth,radius,unit,value,0);
				ctx.fill();
			}
			ctx.globalAlpha = 1;
			/*drawing bar body*/
			ctx.globalAlpha = this._settings.alpha.call(this,data[i]);
			ctx.fillStyle = this._settings.color.call(this,data[i]);
			ctx.beginPath();
			var points = this._setBarHPoints(ctx,x0,y0,barWidth,radius,unit,value,(this._settings.border?1:0));
			if (gradient&&!inner_gradient) ctx.lineTo(point0.x+total_width,y0+(this._settings.border?1:0)); //fix gradient sphreading
   			ctx.fill();
			
			if (inner_gradient!=false){
				var gradParam = this._setBarGradient(ctx,x0,y0+barWidth,x0,y0,inner_gradient,color,"x")
				ctx.fillStyle = gradParam.gradient;
				ctx.beginPath();
				var points = this._setBarHPoints(ctx,x0,y0, barWidth,radius,unit,value,0);
				ctx.fill();
				ctx.globalAlpha = 1;
			}
			
			/*sets a bar label*/
			this.renderTextAt("middle",true,data[i].$startX+(points[0]-data[i].$startX)/2-1, y0+(points[1]-y0)/2, this._settings.label(data[i]));
			/*defines a map area for a bar*/
			map.addRect(data[i].id,[data[i].$startX,y0,points[0],points[1]],sIndex);
			/*the start position for the next series*/
			data[i].$startX = points[0];
		}
	}
}


/* DHX DEPEND FROM FILE 'ext/chart/chart_stackedbar.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
dhtmlx.chart.stackedBar = {
	/**
	*   renders a bar chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: x - the width of the container
	*   @param: y - the height of the container
	*   @param: sIndex - index of drawing chart
	*/
	pvt_render_stackedBar:function(ctx, data, point0, point1, sIndex, map){
	     var maxValue,minValue;
		/*necessary if maxValue - minValue < 0*/
		var valueFactor;
		/*maxValue - minValue*/
		var relValue;
		
		var total_height = point1.y-point0.y;
		
		var yax = !!this._settings.yAxis;
		var xax = !!this._settings.xAxis;
		
		var limits = this._getStackedLimits(data);
		maxValue = limits.max;
		minValue = limits.min;
		
		/*an available width for one bar*/
		var cellWidth = Math.floor((point1.x-point0.x)/data.length);
		
		/*draws x and y scales*/
		if(!sIndex)
			this._drawScales(ctx,data,point0, point1,minValue,maxValue,cellWidth);
		
		/*necessary for automatic scale*/
		if(yax){
		    maxValue = parseFloat(this._settings.yAxis.end);
			minValue = parseFloat(this._settings.yAxis.start);      
		}
		
		/*unit calculation (bar_height = value*unit)*/
		var relativeValues = this._getRelativeValue(minValue,maxValue);
		relValue = relativeValues[0];
		valueFactor = relativeValues[1];
		
		var unit = (relValue?total_height/relValue:10);
		
		/*a real bar width */
		var barWidth = parseInt(this._settings.width,10);
		if(barWidth+4 > cellWidth) barWidth = cellWidth-4;
		/*the half of distance between bars*/
		var barOffset = Math.floor((cellWidth - barWidth)/2);
		
		
		var inner_gradient = (this._settings.gradient?this._settings.gradient:false);
		
		var scaleY = 0;
		/*draws a black line if the horizontal scale isn't defined*/
		if(!xax){
			//scaleY = y-bottomPadding;
			this._drawLine(ctx,point0.x,point1.y+0.5,point1.x,point1.y+0.5,"#000000",1); //hardcoded color!
		}
		
		for(var i=0; i < data.length;i ++){
			var value =  parseFloat(this._settings.value(data[i]));
			if(!value) continue;
			
			/*adjusts the first tab to the scale*/
			if(!sIndex)
				value -= minValue;

			value *= valueFactor;
			
			/*start point (bottom left)*/
			var x0 = point0.x + barOffset + i*cellWidth;
			var y0 = point1.y;
			
			/*for the 2nd, 3rd, etc. series*/
			if(sIndex)
			    y0 = data[i].$startY || y0;

			/*the max height limit*/
			if(y0 < (point0.y+1)) continue;
			
			if(value<0||(this._settings.yAxis&&value===0)){
				this.renderTextAt(true, true, x0+Math.floor(barWidth/2),y0,this._settings.label(data[i]));
				continue;
			}
			
			var color = this._settings.color.call(this,data[i]);
			
			/*drawing the gradient border of a bar*/
			if(this._settings.border){
				ctx.beginPath();
				ctx.fillStyle = color;
				this._setStakedBarPoints(ctx,x0-1,y0,barWidth+2,unit,value,0,point0.y);
				ctx.lineTo(x0,y0);
				ctx.fill();

				ctx.fillStyle = "#000000";
				ctx.globalAlpha = 0.37;
				ctx.beginPath();
				this._setStakedBarPoints(ctx,x0-1,y0,barWidth+2,unit,value,0,point0.y);
				ctx.fill();
			}
			
			/*drawing bar body*/
			ctx.globalAlpha = this._settings.alpha.call(this,data[i]);
			ctx.fillStyle = this._settings.color.call(this,data[i]);
			ctx.beginPath();
			var points = this._setStakedBarPoints(ctx,x0,y0,barWidth,unit,value,(this._settings.border?1:0),point0.y);
   			ctx.fill();
			ctx.globalAlpha = 1;
			
			/*gradient*/
			if (inner_gradient){
				var gradParam = this._setBarGradient(ctx,x0,y0,x0+barWidth,points[1],inner_gradient,color,"y");
				ctx.fillStyle = gradParam.gradient;
				ctx.beginPath();
				var points = this._setStakedBarPoints(ctx,x0+gradParam.offset,y0,barWidth-gradParam.offset*2,unit,value,(this._settings.border?1:0),point0.y);
				ctx.fill();
				ctx.globalAlpha = 1;
			}
			
			/*sets a bar label*/
			this.renderTextAt(false, true, x0+Math.floor(barWidth/2),(points[1]+(y0-points[1])/2)-7,this._settings.label(data[i]));
			/*defines a map area for a bar*/
			map.addRect(data[i].id,[x0,points[1],points[0],(data[i].$startY||y0)],sIndex);
			
			/*the start position for the next series*/
			data[i].$startY = (this._settings.border?(points[1]+1):points[1]);
		}
	},
	/**
	*   sets points for bar and returns the position of the bottom right point
	*   @param: ctx - canvas object
	*   @param: x0 - the x position of start point
	*   @param: y0 - the y position of start point
	*   @param: barWidth - bar width 
	*   @param: radius - the rounding radius of the top
	*   @param: unit - the value defines the correspondence between item value and bar height
	*   @param: value - item value
	*   @param: offset - the offset from expected bar edge (necessary for drawing border)
	*   @param: minY - the minimum y position for the bars ()
	*/
	_setStakedBarPoints:function(ctx,x0,y0,barWidth,unit,value,offset,minY){
		/*start*/
		ctx.moveTo(x0,y0);
		/*start of left rounding*/
		var y1 = y0 - unit*value+offset;
		/*maximum height limit*/
		if(y1<minY) 
			y1 = minY;
		ctx.lineTo(x0,y1);
   		var x3 = x0 + barWidth;
		var y3 = y1; 
		ctx.lineTo(x3,y3);
		/*right rounding*/
		var y4 = y1;
   		/*bottom right point*/
		var x5 = x0 + barWidth;
        ctx.lineTo(x5,y0);
		/*line to the start point*/
   		ctx.lineTo(x0,y0);
   	//	ctx.lineTo(x0,0); //IE fix!
		return [x5,y3-2*offset];
	}
};



/* DHX DEPEND FROM FILE 'ext/chart/chart_line.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
dhtmlx.chart.line = {

	/**
	*   renders a graphic
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: width - the width of the container
	*   @param: height - the height of the container
	*   @param: sIndex - index of drawing chart
	*/
	pvt_render_line:function(ctx, data, point0, point1, sIndex, map){
				
	    var params = this._calculateParametersOfLineChart(ctx,data,point0,point1,sIndex);
		
		/*the value that defines the map area position*/
		var areaPos = Math.floor(params.cellWidth/2);
		
		/*drawing all items*/
		if (data.length) {
		    /*gets the vertical coordinate of an item*/
			
			/*the position of the first item*/
			var y1 = this._getYPointOfLineChart(data[0],point0,point1,params);
			var x1 = (this._settings.offset?point0.x+params.cellWidth*0.5:point0.x);
			var x0 = x1;
			/*drawing the previous item and the line between to items*/
			for(var i=1; i <= data.length;i ++){
								
				/*horizontal positions of the item (0.5 - the fix for line width)*/
				//var x1 = Math.floor(params.cellWidth*(i-0.5)) - 0.5 + point0.x;
				var x2 = Math.floor(params.cellWidth*i) - 0.5 + x0;

				/*a line between items*/
				if (data.length!=i){
					var y2 = this._getYPointOfLineChart(data[i],point0,point1,params);
					this._drawLine(ctx,x1,y1,x2,y2,this._settings.line.color(data[i-1]),this._settings.line.width);
				}
				
				/*draws prevous item*/
				this._drawItemOfLineChart(ctx,x1,y1,data[i-1],!!this._settings.offset);
				
				/*creates map area*/
				map.addRect(data[i-1].id,[x1-areaPos,y1-areaPos,x1+areaPos,y1+areaPos]);
				
				y1=y2;
				x1=x2;
			}
		}
	},
	/**
	*   draws an item and its label
	*   @param: ctx - canvas object
	*   @param: x0 - the x position of a circle
	*   @param: y0 - the y position of a circle
	*   @param: obj - data object 
	*   @param: label - (boolean) defines wherether label needs being drawn 
	*/
	_drawItemOfLineChart:function(ctx,x0,y0,obj,label){
		var R = parseInt(this._settings.item.radius,10);
		ctx.lineWidth = parseInt(this._settings.item.borderWidth,10);
		ctx.fillStyle = this._settings.item.color(obj);
		ctx.strokeStyle = this._settings.item.borderColor(obj);
		ctx.beginPath();
		ctx.arc(x0,y0,R,0,Math.PI*2,true);
		ctx.fill();
		ctx.stroke();
		/*item label*/
		if(label)
			this.renderTextAt(false, true, x0,y0-R-this._settings.labelOffset,this._settings.label(obj));
	},
	/**
	*   gets the vertical position of the item
	*   @param: data - data object
	*   @param: y0 - the y position of chart start
	*   @param: y1 - the y position of chart end
	*   @param: params - the object with elements: minValue, maxValue, unit, valueFactor (the value multiple of 10) 
	*/
	_getYPointOfLineChart: function(data,point0,point1,params){
		var minValue = params.minValue;
		var maxValue = params.maxValue;
		var unit = params.unit;
		var valueFactor = params.valueFactor;
		/*the real value of an object*/
		var value = this._settings.value(data);
		/*a relative value*/
		var v = (parseFloat(value) - minValue)*valueFactor;
		if(!this._settings.yAxis)
			v += params.startValue/unit;
		/*a vertical coordinate*/
		var y = point1.y - Math.floor(unit*v);
		/*the limit of the minimum value is  the minimum visible value*/
		if(v<0) 
			y = point1.y;
		/*the limit of the maximum value*/
		if(value > maxValue) 
			y = point0.y;
		/*the limit of the minimum value*/
		if(value < minValue) 
			y = point1.y;
		return y;
	},
	_calculateParametersOfLineChart: function(ctx,data,point0,point1,sIndex){
		var params = {};
		
		/*maxValue - minValue*/
		var relValue;
		
		/*available height*/
		params.totalHeight = point1.y-point0.y;
		
		/*a space available for a single item*/
		//params.cellWidth = Math.round((point1.x-point0.x)/((!this._settings.offset&&this._settings.yAxis)?(data.length-1):data.length)); 
		params.cellWidth = Math.round((point1.x-point0.x)/((!this._settings.offset)?(data.length-1):data.length)); 
		
		/*scales*/
		var yax = !!this._settings.yAxis;
		var xax = !!this._settings.xAxis;
		
		var limits = (this._settings.view.indexOf("stacked")!=-1?this._getStackedLimits(data):this._getLimits());
		params.maxValue = limits.max;
		params.minValue = limits.min;
		
		/*draws x and y scales*/
		if(!sIndex)
			this._drawScales(ctx,data, point0, point1,params.minValue,params.maxValue,params.cellWidth);
		
		/*necessary for automatic scale*/
		if(yax){
		    params.maxValue = parseFloat(this._settings.yAxis.end);
			params.minValue = parseFloat(this._settings.yAxis.start);      
		}
		
		/*unit calculation (y_position = value*unit)*/
		var relativeValues = this._getRelativeValue(params.minValue,params.maxValue);
		relValue = relativeValues[0];
		params.valueFactor = relativeValues[1];
		params.unit = (relValue?params.totalHeight/relValue:10);
		
		params.startValue = 0;
		if(!yax){
			/*defines start value for better representation of small values*/
			params.startValue = (params.unit>10?params.unit:10);
			params.unit = (relValue?(params.totalHeight - params.startValue)/relValue:10);
		}
		return params;
	}
};



/* DHX DEPEND FROM FILE 'ext/chart/chart_bar.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
dhtmlx.chart.bar = {
	/**
	*   renders a bar chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: x - the width of the container
	*   @param: y - the height of the container
	*   @param: sIndex - index of drawing chart
	*/
	pvt_render_bar:function(ctx, data, point0, point1, sIndex, map){
	     var maxValue,minValue;
		/*necessary if maxValue - minValue < 0*/
		var valueFactor;
		/*maxValue - minValue*/
		var relValue;
		
		var total_height = point1.y-point0.y;
		
		var yax = !!this._settings.yAxis;
		var xax = !!this._settings.xAxis;
		
		var limits = this._getLimits();
		maxValue = limits.max;
		minValue = limits.min;
		
		/*an available width for one bar*/
		var cellWidth = Math.floor((point1.x-point0.x)/data.length);
		
		/*draws x and y scales*/
		if(!sIndex&&!(this._settings.origin!="auto"&&!yax)){
			this._drawScales(ctx,data,point0, point1,minValue,maxValue,cellWidth);
		}
		
		/*necessary for automatic scale*/
		if(yax){
		    maxValue = parseFloat(this._settings.yAxis.end);
			minValue = parseFloat(this._settings.yAxis.start);      
		}
		
		/*unit calculation (bar_height = value*unit)*/
		var relativeValues = this._getRelativeValue(minValue,maxValue);
		relValue = relativeValues[0];
		valueFactor = relativeValues[1];
		
		var unit = (relValue?total_height/relValue:relValue);
		if(!yax&&!(this._settings.origin!="auto"&&xax)){
			/*defines start value for better representation of small values*/
			var startValue = 10;
			unit = (relValue?(total_height-startValue)/relValue:startValue);
		}
		/*if yAxis isn't set, but with custom origin */
		if(!sIndex&&(this._settings.origin!="auto"&&!yax)&&this._settings.origin>minValue){
			this._drawXAxis(ctx,data,point0,point1,cellWidth,point1.y-unit*(this._settings.origin-minValue));
		}
		
		/*a real bar width */
		var barWidth = parseInt(this._settings.width,10);
		if(this._series&&(barWidth*this._series.length+4)>cellWidth) barWidth = cellWidth/this._series.length-4;
		/*the half of distance between bars*/
		var barOffset = Math.floor((cellWidth - barWidth*this._series.length)/2);
		/*the radius of rounding in the top part of each bar*/
		var radius = (typeof this._settings.radius!="undefined"?parseInt(this._settings.radius,10):Math.round(barWidth/5));
		
		var inner_gradient = false;
		var gradient = this._settings.gradient;
		
		if(gradient && typeof(gradient) != "function"){
			inner_gradient = gradient;
			gradient = false;
		} else if (gradient){
			gradient = ctx.createLinearGradient(0,point1.y,0,point0.y);
			this._settings.gradient(gradient);
		}
		var scaleY = 0;
		/*draws a black line if the horizontal scale isn't defined*/
		if(!xax){
			this._drawLine(ctx,point0.x,point1.y+0.5,point1.x,point1.y+0.5,"#000000",1); //hardcoded color!
		}
		
		for(var i=0; i < data.length;i ++){
			
			var value =  parseFloat(this._settings.value(data[i]));
			if(value>maxValue) value = maxValue;
			value -= minValue;
			value *= valueFactor;
			
			/*start point (bottom left)*/
			var x0 = point0.x + barOffset + i*cellWidth+(barWidth+1)*sIndex;
			var y0 = point1.y;
		
			if(value<0||(this._settings.yAxis&&value===0&&!(this._settings.origin!="auto"&&this._settings.origin>minValue))){
				this.renderTextAt(true, true, x0+Math.floor(barWidth/2),y0,this._settings.label(data[i]));
				continue;
			}
			
			/*takes start value into consideration*/
			if(!yax&&!(this._settings.origin!="auto"&&xax)) value += startValue/unit;
			
			var color = gradient||this._settings.color.call(this,data[i]);
	
			/*drawing the gradient border of a bar*/
			if(this._settings.border)
				this._drawBarBorder(ctx,x0,y0,barWidth,minValue,radius,unit,value,color);
			
			/*drawing bar body*/
			ctx.globalAlpha = this._settings.alpha.call(this,data[i]);
			var points = this._drawBar(ctx,point0,x0,y0,barWidth,minValue,radius,unit,value,color,gradient,inner_gradient);
			ctx.globalAlpha = 1;
			
			if (inner_gradient){
				this._drawBarGradient(ctx,x0,y0,barWidth,minValue,radius,unit,value,color,inner_gradient);
			}
			/*sets a bar label*/
			if(points[0]!=x0)
				this.renderTextAt(false, true, x0+Math.floor(barWidth/2),points[1],this._settings.label(data[i]));
			else
				this.renderTextAt(true, true, x0+Math.floor(barWidth/2),points[3],this._settings.label(data[i]));
			/*defines a map area for a bar*/
			map.addRect(data[i].id,[x0,points[3],points[2],points[1]],sIndex);
		}
	},
	_correctBarParams:function(ctx,x,y,value,unit,barWidth,minValue){
		var xax = this._settings.xAxis;
		var axisStart = y;
		if(!!xax&&this._settings.origin!="auto" && (this._settings.origin>minValue)){
			y -= (this._settings.origin-minValue)*unit;
			axisStart = y;
			value = value-(this._settings.origin-minValue);
			if(value < 0){
				value *= (-1);
			 	ctx.translate(x+barWidth,y);
				ctx.rotate(Math.PI);
				x = 0;
				y = 0;
			}
			y -= 0.5;
		}
		
		return {value:value,x0:x,y0:y,start:axisStart}
	},
	_drawBar:function(ctx,point0,x0,y0,barWidth,minValue,radius,unit,value,color,gradient,inner_gradient){
		ctx.save();
		ctx.fillStyle = color;
		var p = this._correctBarParams(ctx,x0,y0,value,unit,barWidth,minValue);
		var points = this._setBarPoints(ctx,p.x0,p.y0,barWidth,radius,unit,p.value,(this._settings.border?1:0));
		if (gradient&&!inner_gradient) ctx.lineTo(p.x0+(this._settings.border?1:0),point0.y); //fix gradient sphreading
   		ctx.fill()
	    ctx.restore();
		var x1 = p.x0;
		var x2 = (p.x0!=x0?x0+points[0]:points[0]);
		var y1 = (p.x0!=x0?(p.start-points[1]):y0);
		var y2 = (p.x0!=x0?p.start:points[1]);
		return [x1,y1,x2,y2];
	},
	_drawBarBorder:function(ctx,x0,y0,barWidth,minValue,radius,unit,value,color){
		ctx.save();
		var p = this._correctBarParams(ctx,x0,y0,value,unit,barWidth,minValue);
		
		ctx.fillStyle = color;
		this._setBarPoints(ctx,p.x0,p.y0,barWidth,radius,unit,p.value,0);
		ctx.lineTo(p.x0,0);
		ctx.fill()
	   
				
		ctx.fillStyle = "#000000";
		ctx.globalAlpha = 0.37;
		
		this._setBarPoints(ctx,p.x0,p.y0,barWidth,radius,unit,p.value,0);
		ctx.fill()
	    ctx.restore();
	},
	_drawBarGradient:function(ctx,x0,y0,barWidth,minValue,radius,unit,value,color,inner_gradient){
		ctx.save();
		//y0 -= (dhtmlx._isIE?0:0.5);
		var p = this._correctBarParams(ctx,x0,y0,value,unit,barWidth,minValue);
		var gradParam = this._setBarGradient(ctx,p.x0,p.y0,p.x0+barWidth,p.y0-unit*p.value+2,inner_gradient,color,"y");
		ctx.fillStyle = gradParam.gradient;
		this._setBarPoints(ctx,p.x0+gradParam.offset,p.y0,barWidth-gradParam.offset*2,radius,unit,p.value,gradParam.offset);
		ctx.fill()
	    ctx.restore();
	},
	/**
	*   sets points for bar and returns the position of the bottom right point
	*   @param: ctx - canvas object
	*   @param: x0 - the x position of start point
	*   @param: y0 - the y position of start point
	*   @param: barWidth - bar width 
	*   @param: radius - the rounding radius of the top
	*   @param: unit - the value defines the correspondence between item value and bar height
	*   @param: value - item value
	*   @param: offset - the offset from expected bar edge (necessary for drawing border)
	*/
	_setBarPoints:function(ctx,x0,y0,barWidth,radius,unit,value,offset){
		/*correction for displaing small values (when rounding radius is bigger than bar height)*/
		ctx.beginPath();
		//y0 = 0.5;
		var angle_corr = 0;
		if(radius>unit*value){
			var cosA = (radius-unit*value)/radius;
			angle_corr = -Math.acos(cosA)+Math.PI/2;
		}
		/*start*/
		ctx.moveTo(x0+offset,y0);
		/*start of left rounding*/
		var y1 = y0 - Math.floor(unit*value) + radius + (radius?0:offset);
		if(radius<unit*value)
			ctx.lineTo(x0+offset,y1);
   		/*left rounding*/
		var x2 = x0 + radius;
		if (radius)
			ctx.arc(x2,y1,radius-offset,-Math.PI+angle_corr,-Math.PI/2,false);
   		/*start of right rounding*/
		var x3 = x0 + barWidth - radius - (radius?0:offset);
		var y3 = y1 - radius+(radius?offset:0);
		ctx.lineTo(x3,y3);
		/*right rounding*/
		var y4 = y1;
		if (radius)
			ctx.arc(x3,y4,radius-offset,-Math.PI/2,0-angle_corr,false);
   		/*bottom right point*/
		var x5 = x0 + barWidth-offset;
        ctx.lineTo(x5,y0);
		/*line to the start point*/
   		ctx.lineTo(x0+offset,y0);
   	//	ctx.lineTo(x0,0); //IE fix!
		return [x5,y3];
	}
};


/* DHX DEPEND FROM FILE 'ext/chart/chart_pie.js'*/


/*DHX:Depend ext/chart/chart_base.js*/
dhtmlx.chart.pie = {
	pvt_render_pie:function(ctx,data,x,y,sIndex,map){
		this._renderPie(ctx,data,x,y,1,map);
		
	}, 
	/**
	*   renders a pie chart
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: x - the width of the container
	*   @param: y - the height of the container
	*   @param: ky - value from 0 to 1 that defines an angle of inclination (0<ky<1 - 3D chart)
	*/
	_renderPie:function(ctx,data,point0,point1,ky,map){
				
		var totalValue = 0;
		var coord = this._getPieParameters(point0,point1);
		/*pie radius*/
		var radius = (this._settings.radius?this._settings.radius:coord.radius);
		var maxValue = this.max(this._settings.value);
		/*weighed values (the ratio of object value to total value)*/
		var ratios = [];
		/*real values*/
		var values = [];
		var prevSum = 0;

		for(var i = 0; i < data.length;i++)
           totalValue += parseFloat(this._settings.value(data[i]));
		
		for(var i = 0; i < data.length;i++){
			values[i] = parseFloat(this._settings.value(data[i]));
			ratios[i] = Math.PI*2*(totalValue?((values[i]+prevSum)/totalValue):(1/data.length));
			prevSum += values[i];
		}
		/*pie center*/
		var x0 = (this._settings.x?this._settings.x:coord.x);
		var y0 = (this._settings.y?this._settings.y:coord.y);
		/*adds shadow to the 2D pie*/
		if(ky==1&&this._settings.shadow)
			this._addShadow(ctx,x0,y0,radius);
		
		/*changes vertical position of the center according to 3Dpie cant*/
		y0 = y0/ky;
		/*the angle defines the 1st edge of the sector*/
		var alpha0 = -Math.PI/2;
		/*changes Canvas vertical scale*/
		ctx.scale(1,ky); 
		
		for(var i = 0; i < data.length;i++){
			if (!values[i]) continue;
			/*drawing sector*/
			ctx.lineWidth = 2;
			ctx.beginPath(); 
	    	ctx.moveTo(x0,y0);
			/*the angle defines the 2nd edge of the sector*/
			alpha1 = -Math.PI/2+ratios[i]-0.0001;
			ctx.arc(x0,y0,radius,alpha0,alpha1,false);
			ctx.lineTo(x0,y0);

			var color = this._settings.color.call(this,data[i]);
			ctx.fillStyle = color;

			ctx.strokeStyle = this._settings.lineColor(data[i]);
			ctx.stroke();
			ctx.fill();

			/*text that needs being displayed inside the sector*/
			if(this._settings.pieInnerText)
				this._drawSectorLabel(x0,y0,5*radius/6,alpha0,alpha1,ky,this._settings.pieInnerText(data[i],totalValue),true);
			/*label outside the sector*/
			if(this._settings.label)
				this._drawSectorLabel(x0,y0,radius+this._settings.labelOffset,alpha0,alpha1,ky,this._settings.label(data[i]));
			/*drawing lower part for 3D pie*/
			if(ky!=1){
				this._createLowerSector(ctx,x0,y0,alpha0,alpha1,radius,true);
				ctx.fillStyle = "#000000";
				ctx.globalAlpha = 0.2;
				this._createLowerSector(ctx,x0,y0,alpha0,alpha1,radius,false);
				ctx.globalAlpha = 1;
				ctx.fillStyle = color;
			}
			
			/*creats map area (needed for events)*/
			map.addSector(data[i].id,alpha0,alpha1,x0,y0,radius,ky);
			
			alpha0 = alpha1;
			
			
		}
		
		/*adds radial gradient to a pie*/
		if (this._settings.gradient){
			var x1 = (ky!=1?x0+radius/3:x0);
			var y1 = (ky!=1?y0+radius/3:y0);
			this._showRadialGradient(ctx,x0,y0,radius,x1,y1);	
		}
		ctx.scale(1,1/ky); 
	},
	/**
	*   returns calculated pie parameters: center position and radius
	*   @param: x - the width of a container
	*   @param: y - the height of a container
	*/
	_getPieParameters:function(point0,point1){
		/*var offsetX = 0;
		var offsetY = 0;
		if(this._settings.legend &&this._settings.legend.layout!="x")
			offsetX = this._settings.legend.width*(this._settings.legend.align=="right"?-1:1);
		var x0 = (x + offsetX)/2;
		if(this._settings.legend &&this._settings.legend.layout=="x")
			offsetY = this._settings.legend.height*(this._settings.legend.valign=="bottom"?-1:1);
		var y0 = (y+offsetY)/2;*/
		var width = point1.x-point0.x;
		var height = point1.y-point0.y;
		var x0 = point0.x+width/2;
		var y0 = point0.y+height/2
		var radius = Math.min(width/2,height/2);
		return {"x":x0,"y":y0,"radius":radius};
	},
	/**
	*   creates lower part of sector in 3Dpie
	*   @param: ctx - canvas object
	*   @param: x0 - the horizontal position of the pie center
	*   @param: y0 - the vertical position of the pie center
	*   @param: a0 - the angle that defines the first edge of a sector
	*   @param: a1 - the angle that defines the second edge of a sector
	*   @param: R - pie radius
	*   @param: line (boolean) - if the sector needs a border
	*/
	_createLowerSector:function(ctx,x0,y0,a1,a2,R,line){
		ctx.lineWidth = 1;
		/*checks if the lower sector needs being displayed*/
		if(!((a1<=0 && a2>=0)||(a1>=0 && a2<=Math.PI)||(a1<=Math.PI && a2>=Math.PI))) return;
		
		if(a1<=0 && a2>=0){
			a1 = 0;
			line = false;
			this._drawSectorLine(ctx,x0,y0,R,a1,a2);
		}
		if(a1<=Math.PI && a2>=Math.PI){
			a2 = Math.PI;
			line = false;
			this._drawSectorLine(ctx,x0,y0,R,a1,a2);
		}
		/*the height of 3D pie*/
		var offset = (this._settings.height||Math.floor(R/4))/this._settings.cant;
		ctx.beginPath(); 
		ctx.arc(x0,y0,R,a1,a2,false);
		ctx.lineTo(x0+R*Math.cos(a2),y0+R*Math.sin(a2)+offset);
		ctx.arc(x0,y0+offset,R,a2,a1,true);
		ctx.lineTo(x0+R*Math.cos(a1),y0+R*Math.sin(a1));
		ctx.fill();
		if(line)		
			ctx.stroke();
	},
	/**
	*   draws a serctor arc
	*/
	_drawSectorLine:function(ctx,x0,y0,R,a1,a2){
		ctx.beginPath(); 
		ctx.arc(x0,y0,R,a1,a2,false);
		ctx.stroke();
	},
	/**
	*   adds a shadow to pie
	*   @param: ctx - canvas object
	*   @param: x - the horizontal position of the pie center
	*   @param: y - the vertical position of the pie center
	*   @param: R - pie radius
	*/
	_addShadow:function(ctx,x,y,R){
		var shadows = ["#676767","#7b7b7b","#a0a0a0","#bcbcbc","#d1d1d1","#d6d6d6"];
		for(var i = shadows.length-1;i>-1;i--){
			ctx.beginPath();
			ctx.fillStyle = shadows[i]; 
			ctx.arc(x+2,y+2,R+i,0,Math.PI*2,true);  
			ctx.fill();  
		} 
	},
	/**
		*   returns a gray gradient
		*   @param: gradient - gradient object
	*/
	_getGrayGradient:function(gradient){
		gradient.addColorStop(0.0,"#ffffff");
		gradient.addColorStop(0.7,"#7a7a7a");
		gradient.addColorStop(1.0,"#000000");
		return gradient;
	},
	/**
	*   adds gray radial gradient
	*   @param: ctx - canvas object
	*   @param: x - the horizontal position of the pie center
	*   @param: y - the vertical position of the pie center
	*   @param: radius - pie radius
	*   @param: x0 - the horizontal position of a gradient center
	*   @param: y0 - the vertical position of a gradient center
	*/
	_showRadialGradient:function(ctx,x,y,radius,x0,y0){
			ctx.globalAlpha = 0.3;
			ctx.beginPath();
			var gradient; 
			if(typeof this._settings.gradient!= "function"){
				gradient = ctx.createRadialGradient(x0,y0,radius/4,x,y,radius);
				gradient = this._getGrayGradient(gradient);
			}
			else gradient = this._settings.gradient(gradient);
			ctx.fillStyle = gradient;
			ctx.arc(x,y,radius,0,Math.PI*2,true);
			ctx.fill();
			ctx.globalAlpha = 1;
	},
	/**
	*   returns the calculates pie parameters: center position and radius
	*   @param: ctx - canvas object
	*   @param: x0 - the horizontal position of the pie center
	*   @param: y0 - the vertical position of the pie center
	*   @param: R - pie radius
	*   @param: alpha1 - the angle that defines the 1st edge of a sector
	*   @param: alpha2 - the angle that defines the 2nd edge of a sector
	*   @param: ky - the value that defines an angle of inclination
	*   @param: text - label text
	*   @param: in_width (boolean) - if label needs being displayed inside a pie
	*/
	_drawSectorLabel:function(x0,y0,R,alpha1,alpha2,ky,text,in_width){
		var t = this.renderText(0,0,text,0,1);
		if (!t) return;
		
		//get existing width of text
		var labelWidth = t.scrollWidth;
		t.style.width = labelWidth+"px";	//adjust text label to fit all text
		if (labelWidth>x0) labelWidth = x0;	//the text can't be greater than half of view
		
		//calculate expected correction based on default font metrics
		var width = 8;
		if (in_width) width = labelWidth/1.8;
		var alpha = alpha1+(alpha2-alpha1)/2;
		
		//calcualteion position and correction
		R = R-(width-8)/2;
		var corr_x = - width;
		var corr_y = -8;
		var align = "left";
		
		//for items in right upper sector
		if(alpha>=Math.PI/2 && alpha<Math.PI){
			//correction need to be applied because of righ align
			//we need to count right upper angle instead of left upper angle
			corr_x = -labelWidth-corr_x+1;/*correction for label width*/
			align = "right";
		}
		//for items in right lower sector
		if(alpha<=3*Math.PI/2 && alpha>=Math.PI){
			corr_x = -labelWidth-corr_x+1;
			align = "right";
		}
		
		//calculate position of text
		//basically get point at center of pie sector
		var y = (y0+Math.floor(R*Math.sin(alpha)))*ky+corr_y;
		var x = x0+Math.floor((R+width/2)*Math.cos(alpha))+corr_x;
		
		//if pie sector starts in left of right part pie, related text
		//must be placed to the left of to the right of pie as well
		var left_end = (alpha2 < Math.PI/2+0.01)
		var left_start = (alpha < Math.PI/2);
		if (left_start && left_end)
			x = Math.max(x,x0+3);	//right part of pie
		else if (!left_start && !left_end)
			x = Math.min(x,x0-labelWidth);	//left part of pie
		
		/*correction for the lower sector of the 3D pie*/
		if (!in_width && ky<1 && y > y0*ky){
			y+= (this._settings.height||Math.floor(R/4));
		}

		//we need to set position of text manually, based on above calculations
		t.style.top  = y+"px";
		t.style.left = x+"px";
		t.style.width = labelWidth+"px";
		t.style.textAlign = align;
		t.style.whiteSpace = "nowrap";
	}
};

dhtmlx.chart.pie3D = {
	pvt_render_pie3D:function(ctx,data,x,y,sIndex,map){
		this._renderPie(ctx,data,x,y,this._settings.cant,map);
	}
}


/* DHX DEPEND FROM FILE 'template.js'*/


/*
	Template - handles html templates
*/

/*DHX:Depend dhtmlx.js*/

dhtmlx.Template={
	_cache:{
	},
	empty:function(){	
		return "";	
	},
	setter:function(name, value){
		return dhtmlx.Template.fromHTML(value);
	},
	obj_setter:function(name,value){
		var f = dhtmlx.Template.setter(name,value);
		var obj = this;
		return function(){
			return f.apply(obj, arguments);
		};
	},
	fromHTML:function(str){
		if (typeof str == "function") return str;
		if (this._cache[str])
			return this._cache[str];
			
	//supported idioms
	// {obj} => value
	// {obj.attr} => named attribute or value of sub-tag in case of xml
	// {obj.attr?some:other} conditional output
	// {-obj => sub-template
		str=(str||"").toString();		
		str=str.replace(/[\r\n]+/g,"\\n");
		str=str.replace(/\{obj\.([^}?]+)\?([^:]*):([^}]*)\}/g,"\"+(obj.$1?\"$2\":\"$3\")+\"");
		str=str.replace(/\{common\.([^}\(]*)\}/g,"\"+common.$1+\"");
		str=str.replace(/\{common\.([^\}\(]*)\(\)\}/g,"\"+(common.$1?common.$1(obj):\"\")+\"");
		str=str.replace(/\{obj\.([^}]*)\}/g,"\"+obj.$1+\"");
		str=str.replace(/#([a-z0-9_]+)#/gi,"\"+obj.$1+\"");
		str=str.replace(/\{obj\}/g,"\"+obj+\"");
		str=str.replace(/\{-obj/g,"{obj");
		str=str.replace(/\{-common/g,"{common");
		str="return \""+str+"\";";
		return this._cache[str]= Function("obj","common",str);
	}
};

dhtmlx.Type={
	/*
		adds new template-type
		obj - object to which template will be added
		data - properties of template
	*/
	add:function(obj, data){ 
		//auto switch to prototype, if name of class was provided
		if (!obj.types && obj.prototype.types)
			obj = obj.prototype;
		//if (typeof data == "string")
		//	data = { template:data };
			
		if (dhtmlx.assert_enabled())
			this.assert_event(data);
		
		var name = data.name||"default";
		
		//predefined templates - autoprocessing
		this._template(data);
		this._template(data,"edit");
		this._template(data,"loading");
		
		obj.types[name]=dhtmlx.extend(dhtmlx.extend({},(obj.types[name]||this._default)),data);	
		return name;
	},
	//default template value - basically empty box with 5px margin
	_default:{
		css:"default",
		template:function(){ return ""; },
		template_edit:function(){ return ""; },
		template_loading:function(){ return "..."; },
		width:150,
		height:80,
		margin:5,
		padding:0
	},
	//template creation helper
	_template:function(obj,name){ 
		name = "template"+(name?("_"+name):"");
		var data = obj[name];
		//if template is a string - check is it plain string or reference to external content
		if (data && (typeof data == "string")){
			if (data.indexOf("->")!=-1){
				data = data.split("->");
				switch(data[0]){
					case "html": 	//load from some container on the page
						data = dhtmlx.html.getValue(data[1]).replace(/\"/g,"\\\"");
						break;
					case "http": 	//load from external file
						data = new dhtmlx.ajax().sync().get(data[1],{uid:(new Date()).valueOf()}).responseText;
						break;
					default:
						//do nothing, will use template as is
						break;
				}
			}
			obj[name] = dhtmlx.Template.fromHTML(data);
		}
	}
};



/* DHX DEPEND FROM FILE 'single_render.js'*/


/*
	REnders single item. 
	Can be used for elements without datastore, or with complex custom rendering logic
	
	@export
		render
*/

/*DHX:Depend template.js*/

dhtmlx.SingleRender={
	_init:function(){
	},
	//convert item to the HTML text
	_toHTML:function(obj){
			/*
				this one doesn't support per-item-$template
				it has not sense, because we have only single item per object
			*/
			return this.type._item_start(obj,this.type)+this.type.template(obj,this.type)+this.type._item_end;
	},
	//render self, by templating data object
	render:function(){
		if (!this.callEvent || this.callEvent("onBeforeRender",[this.data])){
			if (this.data)
				this._dataobj.innerHTML = this._toHTML(this.data);
			if (this.callEvent) this.callEvent("onAfterRender",[]);
		}
	}
};


/* DHX DEPEND FROM FILE 'tooltip.js'*/


/*
	UI: Tooltip
	
	@export
		show
		hide
*/

/*DHX:Depend tooltip.css*/
/*DHX:Depend template.js*/
/*DHX:Depend single_render.js*/

dhtmlx.ui.Tooltip=function(container){
	this.name = "Tooltip";
	this.version = "3.0";
	
	if (dhtmlx.assert_enabled()) this._assert();

	if (typeof container == "string"){
		container = { template:container };
	}
		
	dhtmlx.extend(this, dhtmlx.Settings);
	dhtmlx.extend(this, dhtmlx.SingleRender);
	this._parseSettings(container,{
		type:"default",
		dy:0,
		dx:20
	});
	
	//create  container for future tooltip
	this._dataobj = this._obj = document.createElement("DIV");
	this._obj.className="dhx_tooltip";
	dhtmlx.html.insertBefore(this._obj,document.body.firstChild);
};
dhtmlx.ui.Tooltip.prototype = {
	//show tooptip
	//pos - object, pos.x - left, pox.y - top
	show:function(data,pos){
		if (this._disabled) return;
		//render sefl only if new data was provided
		if (this.data!=data){
			this.data=data;
			this.render(data);
		}
		//show at specified position
		this._obj.style.top = pos.y+this._settings.dy+"px";
		this._obj.style.left = pos.x+this._settings.dx+"px";
		this._obj.style.display="block";
	},
	//hide tooltip
	hide:function(){
		this.data=null; //nulify, to be sure that on next show it will be fresh-rendered
		this._obj.style.display="none";
	},
	disable:function(){
		this._disabled = true;	
	},
	enable:function(){
		this._disabled = false;
	},
	types:{
		"default":dhtmlx.Template.fromHTML("{obj.id}")
	},
	template_item_start:dhtmlx.Template.empty,
	template_item_end:dhtmlx.Template.empty
};



/* DHX DEPEND FROM FILE 'autotooltip.js'*/


/*
	Behavior: AutoTooltip - links tooltip to data driven item
*/

/*DHX:Depend tooltip.js*/

dhtmlx.AutoTooltip = {
	tooltip_setter:function(mode,value){
		var t = new dhtmlx.ui.Tooltip(value);
		this.attachEvent("onMouseMove",function(id,e){	//show tooltip on mousemove
			t.show(this.get(id),dhtmlx.html.pos(e));
		});
		this.attachEvent("onMouseOut",function(id,e){	//hide tooltip on mouseout
			t.hide();
		});
		this.attachEvent("onMouseMoving",function(id,e){	//hide tooltip just after moving start
			t.hide();
		});
		return t;
	}
};


/* DHX DEPEND FROM FILE 'datastore.js'*/


/*DHX:Depend dhtmlx.js*/

/*
	DataStore is not a behavior, it standalone object, which represents collection of data.
	Call provideAPI to map data API

	@export
		exists
		idByIndex
		indexById
		get
		set
		refresh
		dataCount
		sort
		filter
		next
		previous
		clearAll
		first
		last
*/
dhtmlx.DataStore = function(){
	this.name = "DataStore";
	
	dhtmlx.extend(this, dhtmlx.EventSystem);
	
	this.setDriver("xml");	//default data source is an XML
	this.pull = {};						//hash of IDs
	this.order = dhtmlx.toArray();		//order of IDs
	this._tree_store = false;
};

dhtmlx.DataStore.prototype={
	//defines type of used data driver
	//data driver is an abstraction other different data formats - xml, json, csv, etc.
	setDriver:function(type){
		dhtmlx.assert(dhtmlx.DataDriver[type],"incorrect DataDriver");
		this.driver = dhtmlx.DataDriver[type];
	},
	_tree_parse:function(data){
		if (data.item){ //FIXME
			if (!(data.item instanceof Array))
				data.item=[data.item];
			for (var i=0; i < data.item.length; i++) {
				var item = data.item[i];
				var id = this.id(item);
				
				data.item[i]=id;	
				this.pull[id]=item;
				item.parent = data.id;
				item.level = data.level+1;
				this._tree_parse(item);
			};
		}
	},
	//process incoming raw data
	_parse:function(data){
		//get size and position of data
		var info = this.driver.getInfo(data);
		//get array of records
		
		var recs = this.driver.getRecords(data);
		var from = (info._from||0)*1;
		var j=0;
		for (var i=0; i<recs.length; i++){
			//get has of details for each record
			var temp = this.driver.getDetails(recs[i]);
			var id = this.id(temp); 	//generate ID for the record
			if (!this.pull[id]){		//if such ID already exists - update instead of insert
				this.order[j+from]=id;	
				j++;
			}
			this.pull[id]=temp;
			if (this._tree_store){
				temp.level = 1;
				this._tree_parse(temp);
			}
		}
		
		//for all not loaded data
		for (var i=0; i < info._size; i++)
			if (!this.order[i]){
				var id = dhtmlx.uid();
				var temp = {id:id, $template:"loading"};	//create fake records
				this.pull[id]=temp;
				this.order[i]=id;
			}
		this.callEvent("onStoreLoad",[this.driver, data]);
		//repaint self after data loading
		this.refresh();
	},
	//generate id for data object
	id:function(data){
		return data.id||(data.id=dhtmlx.uid());
	},
	//get data from hash by id
	get:function(id){
		return this.pull[id];
	},
	//assigns data by id
	set:function(id,data){
		this.pull[id]=data;
		this.refresh();
	},
	//sends repainting signal
	refresh:function(id){
		if (id)
			this.callEvent("onStoreUpdated",[id, this.pull[id], "update"]);
		else
			this.callEvent("onStoreUpdated",[null,null,null]);
	},
	//converts range IDs to array of all IDs between them
	getRange:function(from,to){		
		if (!arguments.length){
			//if indexes not provided - return all visible rows
			from = this.min||0; to = Math.min((this.max||Infinity),(this.dataCount()-1));
		} else{
			from = this.indexById(from);
			to = this.indexById(to);
			if (from>to){ //can be in case of backward shift-selection
				var a=to; to=from; from=a;
			}
		}
		return this.getIndexRange(from,to);
	},
	//converts range of indexes to array of all IDs between them
	getIndexRange:function(from,to){
		to=Math.min(to,this.dataCount()-1);
		
		var ret=dhtmlx.toArray(); //result of method is rich-array
		for (var i=from; i <= to; i++)
			ret.push(this.get(this.order[i]));
		return ret;
	},
	//returns total count of elements
	dataCount:function(){
		return this.order.length;
	},
	//returns truy if item with such ID exists
	exists:function(id){
		return !!(this.pull[id]);
	},
	//nextmethod is not visible on component level, check DataMove.move
	//moves item from source index to the target index
	move:function(sindex,tindex){
		if (sindex<0 || tindex<0){
			dhtmlx.error("DataStore::move","Incorrect indexes");
			return;
		}
		
		var id = this.idByIndex(sindex);
		var obj = this.get(id);
		
		this.order.removeAt(sindex);	//remove at old position
		//if (sindex<tindex) tindex--;	//correct shift, caused by element removing
		this.order.insertAt(id,Math.min(this.order.length, tindex));	//insert at new position
		
		//repaint signal
		this.callEvent("onStoreUpdated",[id,obj,"move"]);
	},
	//adds item to the store
	add:function(obj,index){
		//generate id for the item
		var id = this.id(obj);
		
		//by default item is added to the end of the list
		var data_size = this.dataCount();
		if (dhtmlx.isNotDefined(index) || index < 0)
			index = data_size; 
		//check to prevent too big indexes			
		if (index > data_size){
			dhtmlx.log("Warning","DataStore:add","Index of out of bounds");
			index = Math.min(this.order.length,index);
		} 
		
		if (!this.callEvent("onbeforeAdd",[id,index])) return;	
		
		if (this.exists(id)) return dhtmlx.error("Not unique ID");
		
		this.pull[id]=obj;
		this.order.insertAt(id,index);
		if (this._filter_order){	//adding during filtering
			//we can't know the location of new item in full dataset, making suggestion
			//put at end by default
			var original_index = this._filter_order.length;
			//put at start only if adding to the start and some data exists
			if (!index && this.order.length)
				original_index = 0;
			
			this._filter_order.insertAt(id,original_index);
		}
		
		this.callEvent("onafterAdd",[id,index]);
		//repaint signal
		this.callEvent("onStoreUpdated",[id,obj,"add"]);
		return id;
	},
	
	//removes element from datastore
	remove:function(id){
		//id can be an array of IDs - result of getSelect, for example
		if (id instanceof Array){
			for (var i=0; i < id.length; i++)
				this.remove(id[i]);
			return;
		}
		if (!this.callEvent("onbeforedelete",[id])) return;	
		if (!this.exists(id)) return dhtmlx.error("Not existing ID",id);
		var obj = this.get(id);	//save for later event
		//clear from collections
		this.order.remove(id);
		if (this._filter_order) 
			this._filter_order.remove(id);
			
		delete this.pull[id];
		this.callEvent("onafterdelete",[id]);	
		//repaint signal
		this.callEvent("onStoreUpdated",[id,obj,"delete"]);
	},
	//deletes all records in datastore
	clearAll:function(){
		//instead of deleting one by one - just reset inner collections
		this.pull = {};
		this.order = dhtmlx.toArray();
		this._filter_order = null;
		this.callEvent("onClearAll",[]);
		this.refresh();
	},
	//converts id to index
	idByIndex:function(index){
		if (index>=this.order.length || index<0)
			dhtmlx.log("Warning","DataStore::idByIndex Incorrect index");
			
		return this.order[index];
	},
	//converts index to id
	indexById:function(id){
		var res = this.order.find(id);	//slower than idByIndex
		
		if (res == -1)
			dhtmlx.log("Warning","DataStore::indexById Non-existing ID: "+ id);
			
		return res;
	},
	//returns ID of next element
	next:function(id,step){
		return this.order[this.indexById(id)+(step||1)];
	},
	//returns ID of first element
	first:function(){
		return this.order[0];
	},
	//returns ID of last element
	last:function(){
		return this.order[this.order.length-1];
	},
	//returns ID of previous element
	previous:function(id,step){
		return this.order[this.indexById(id)-(step||1)];
	},
	/*
		sort data in collection
			by - settings of sorting
		
		or
		
			by - sorting function
			dir - "asc" or "desc"
			
		or
		
			by - property
			dir - "asc" or "desc"
			as - type of sortings
		
		Sorting function will accept 2 parameters and must return 1,0,-1, based on desired order
	*/
	sort:function(by, dir, as){
		var sort = by;	
		if (typeof by == "function")
			sort = {as:by, dir:dir};
		else if (typeof by == "string")
			sort = {by:by, dir:dir, as:as};		
		
		
		var parameters = [sort.by, sort.dir, sort.as];
		if (!this.callEvent("onbeforesort",parameters)) return;	
		
		if (this.order.length){
			var sorter = dhtmlx.sort.create(sort);
			//get array of IDs
			var neworder = this.getRange(this.first(), this.last());
			neworder.sort(sorter);
			this.order = neworder.map(function(obj){ return this.id(obj); },this);
		}
		
		//repaint self
		this.refresh();
		
		this.callEvent("onaftersort",parameters);
	},
	/*
		Filter datasource
		
		text - property, by which filter
		value - filter mask
		
		or
		
		text  - filter method
		
		Filter method will receive data object and must return true or false
	*/
	filter:function(text,value){
		//remove previous filtering , if any
		if (this._filter_order){
			this.order = this._filter_order;
			delete this._filter_order;
		}
		//if text not define -just unfilter previous state and exit
		if (text){
			var filter = text;
			if (typeof text == "string"){
				text = dhtmlx.Template.setter(0,text);
				filter = function(obj,value){	//default filter - string start from, case in-sensitive
					return text(obj).toLowerCase().indexOf(value)!=-1;
				};
			}
			
			value = (value||"").toString().toLowerCase();			
			var neworder = dhtmlx.toArray();
			this.order.each(function(id){
				if (filter(this.get(id),value))
					neworder.push(id);
			},this);
			//set new order of items, store original
			this._filter_order = this.order;
			this.order = neworder;
		}
		//repaint self
		this.refresh();
	},
	/*
		Iterate through collection
	*/
	each:function(method,master){
		for (var i=0; i<this.order.length; i++)
			method.call((master||this), this.get(this.order[i]));
	},
	/*
		map inner methods to some distant object
	*/
	provideApi:function(target,eventable){
		
		if (eventable){
			this.mapEvent({
				onbeforesort:	target,
				onaftersort:	target,
				onbeforeadd:	target,
				onafteradd:		target,
				onbeforedelete:	target,
				onafterdelete:	target	
			});
		}
			
		var list = ["sort","add","remove","exists","idByIndex","indexById","get","set","refresh","dataCount","filter","next","previous","clearAll","first","last"];
		for (var i=0; i < list.length; i++)
			target[list[i]]=dhtmlx.methodPush(this,list[i]);
			
		if (dhtmlx.assert_enabled())		
			this.assert_event(target);
	}
};

dhtmlx.sort = {
	create:function(config){
		return dhtmlx.sort.dir(config.dir, dhtmlx.sort.by(config.by, config.as));
	},
	as:{
		"int":function(a,b){
			a = a*1; b=b*1;
			return a>b?1:(a<b?-1:0);
		},
		"string_strict":function(a,b){
			a = a.toString(); b=b.toString();
			return a>b?1:(a<b?-1:0);
		},
		"string":function(a,b){
			a = a.toString().toLowerCase(); b=b.toString().toLowerCase();
			return a>b?1:(a<b?-1:0);
		}
	},
	by:function(prop, method){
		if (typeof method != "function")
			method = dhtmlx.sort.as[method||"string"];
		prop = dhtmlx.Template.setter(0,prop);
		return function(a,b){
			return method(prop(a),prop(b));
		};
	},
	dir:function(prop, method){
		if (prop == "asc")
			return method;
		return function(a,b){
			return method(a,b)*-1;
		};
	}
};


/* DHX DEPEND FROM FILE 'group.js'*/


/*DHX:Depend datastore.js*/
/*DHX:Depend dhtmlx.js*/

dhtmlx.Group = {
	_init:function(){
		dhtmlx.assert(this.data,"DataStore required for grouping");
		this.data.attachEvent("onStoreLoad",dhtmlx.bind(function(){
			if (this._settings.group)
				this.group(this._settings.group,false);
		},this));
		this.attachEvent("onBeforeRender",dhtmlx.bind(function(data){
			if (this._settings.sort){
				data.block();
				data.sort(this._settings.sort);
				data.unblock();
			}
		},this));
		this.attachEvent("onBeforeSort",dhtmlx.bind(function(){
			this._settings.sort = null;
		},this));
	},
	_init_group_data_event:function(data,master){
		data.attachEvent("onClearAll",dhtmlx.bind(function(){
			this.ungroup(false);
		},master));		
	},
	sum:function(property, data){
		property = dhtmlx.Template.setter(0,property);
		
		data = data || this.data;
		var summ = 0; 
		data.each(function(obj){
			summ+=property(obj)*1;
		});
		return summ;
	},
	min:function(property, data){
		property = dhtmlx.Template.setter(0,property);
		
		data = data || this.data;
		var min = Infinity; 
		data.each(function(obj){
			if (property(obj)*1 < min) min = property(obj)*1;
		});
		return min*1;
	},
	max:function(property, data){
		property = dhtmlx.Template.setter(0,property);
		
		data = data || this.data;
		var max = -Infinity;
		data.each(function(obj){
			if (property(obj)*1 > max) max = property(obj)*1;
		});
		return max;
	},
	_split_data_by:function(stats){ 
		var any=function(property, data){
			property = dhtmlx.Template.setter(0,property);
			return property(data[0]);
		};
		var key = dhtmlx.Template.setter(0,stats.by);
		if (!stats.map[key])
			stats.map[key] = [key, any];
			
		var groups = {};
		var labels = [];
		this.data.each(function(data){
			var current = key(data);
			if (!groups[current]){
				labels.push({id:current});
				groups[current] = dhtmlx.toArray();
			}
			groups[current].push(data);
		});
		for (var prop in stats.map){
			var functor = (stats.map[prop][1]||any);
			if (typeof functor != "function")
				functor = this[functor];
				
			for (var i=0; i < labels.length; i++) {
				labels[i][prop]=functor.call(this, stats.map[prop][0], groups[labels[i].id]);
			}
		}
//		if (this._settings.sort)
//			labels.sortBy(stats.sort);
			
		this._not_grouped_data = this.data;
		this.data = new dhtmlx.DataStore();
		this.data.provideApi(this,true);
		this._init_group_data_event(this.data, this);
		this.parse(labels,"json");
	},
	group:function(config,mode){
		this.ungroup(false);
		this._split_data_by(config);
		if (mode!==false)
			this.render();
	},
	ungroup:function(mode){
		if (this._not_grouped_data){
			this.data = this._not_grouped_data;
			this.data.provideApi(this, true);
		}
		if (mode!==false)
			this.render();
	},
	group_setter:function(name, config){
		dhtmlx.assert(typeof config == "object", "Incorrect group value");
		dhtmlx.assert(config.by,"group.by is mandatory");
		dhtmlx.assert(config.map,"group.map is mandatory");
		return config;
	},
	//need to be moved to more appropriate object
	sort_setter:function(name, config){
		if (typeof config != "object")
			config = { by:config };
		
		this._mergeSettings(config,{
			as:"string",
			dir:"asc"
		});
		return config;
	}
};


/* DHX DEPEND FROM FILE 'key.js'*/


/*
	Behavior:KeyEvents - hears keyboard 
*/
dhtmlx.KeyEvents = {
	_init:function(){
		//attach handler to the main container
		dhtmlx.event(this._obj,"keypress",this._onKeyPress,this);
	},
	//called on each key press , when focus is inside of related component
	_onKeyPress:function(e){
		e=e||event;
		var code = e.which||e.keyCode; //FIXME  better solution is required
		this.callEvent((this._edit_id?"onEditKeyPress":"onKeyPress"),[code,e.ctrlKey,e.shiftKey,e]);
	}
};


/* DHX DEPEND FROM FILE 'mouse.js'*/


/*
	Behavior:MouseEvents - provides inner evnets for  mouse actions
*/
dhtmlx.MouseEvents={
	_init: function(){
		//attach dom events if related collection is defined
		if (this.on_click){
			dhtmlx.event(this._obj,"click",this._onClick,this);
			dhtmlx.event(this._obj,"contextmenu",this._onContext,this);
		}
		if (this.on_dblclick)
			dhtmlx.event(this._obj,"dblclick",this._onDblClick,this);
		if (this.on_mouse_move){
			dhtmlx.event(this._obj,"mousemove",this._onMouse,this);
			dhtmlx.event(this._obj,(dhtmlx._isIE?"mouseleave":"mouseout"),this._onMouse,this);
		}

	},
	//inner onclick object handler
	_onClick: function(e) {
		return this._mouseEvent(e,this.on_click,"ItemClick");
	},
	//inner ondblclick object handler
	_onDblClick: function(e) {
		return this._mouseEvent(e,this.on_dblclick,"ItemDblClick");
	},
	//process oncontextmenu events
	_onContext: function(e) {
		var id = dhtmlx.html.locate(e, this._id);
		if (id && !this.callEvent("onBeforeContextMenu", [id,e]))
			return dhtmlx.html.preventEvent(e);
	},
	/*
		event throttler - ignore events which occurs too fast
		during mouse moving there are a lot of event firing - we need no so much
		also, mouseout can fire when moving inside the same html container - we need to ignore such fake calls
	*/
	_onMouse:function(e){
		if (dhtmlx._isIE)	//make a copy of event, will be used in timed call
			e = document.createEventObject(event);
			
		if (this._mouse_move_timer)	//clear old event timer
			window.clearTimeout(this._mouse_move_timer);
				
		//this event just inform about moving operation, we don't care about details
		this.callEvent("onMouseMoving",[e]);
		//set new event timer
		this._mouse_move_timer = window.setTimeout(dhtmlx.bind(function(){
			//called only when we have at least 100ms after previous event
			if (e.type == "mousemove")
				this._onMouseMove(e);
			else
				this._onMouseOut(e);
		},this),500);
	},
	//inner mousemove object handler
	_onMouseMove: function(e) {
		if (!this._mouseEvent(e,this.on_mouse_move,"MouseMove"))
			this.callEvent("onMouseOut",[e||event]);
	},
	//inner mouseout object handler
	_onMouseOut: function(e) {
		this.callEvent("onMouseOut",[e||event]);
	},
	//common logic for click and dbl-click processing
	_mouseEvent:function(e,hash,name){
		e=e||event;
		var trg=e.target||e.srcElement;
		var css = "";
		var id = null;
		var found = false;
		//loop through all parents
		while (trg && trg.parentNode){
			if (!found && trg.getAttribute){													//if element with ID mark is not detected yet
				id = trg.getAttribute(this._id);							//check id of current one
				if (id){
					if (trg.getAttribute("userdata"))
						this.callEvent("onLocateData",[id,trg]);
					if (!this.callEvent("on"+name,[id,e,trg])) return;		//it will be triggered only for first detected ID, in case of nested elements
					found = true;											//set found flag
				}
			}
			css=trg.className;
			if (css){		//check if pre-defined reaction for element's css name exists
				css = css.split(" ");
				css = css[0]||css[1]; //FIXME:bad solution, workaround css classes which are starting from whitespace
				if (hash[css])
					return hash[css].call(this,e,id,trg);
			}
			trg=trg.parentNode;
		}		
		return found;	//returns true if item was located and event was triggered
	}
};


/* DHX DEPEND FROM FILE 'config.js'*/


/*
	Behavior:Settings
	
	@export
		customize
		config
*/

/*DHX:Depend template.js*/
/*DHX:Depend dhtmlx.js*/

dhtmlx.Settings={
	_init:function(){
		/* 
			property can be accessed as this.config.some
			in same time for inner call it have sense to use _settings
			because it will be minified in final version
		*/
		this._settings = this.config= {}; 
	},
	define:function(property, value){
		if (typeof property == "object")
			return this._parseSeetingColl(property);
		return this._define(property, value);
	},
	_define:function(property,value){
		dhtmlx.assert_settings.call(this,property,value);
		
		//method with name {prop}_setter will be used as property setter
		//setter is optional
		var setter = this[property+"_setter"];
		return this._settings[property]=setter?setter.call(this,property,value):value;
	},
	//process configuration object
	_parseSeetingColl:function(coll){
		if (coll){
			for (var a in coll)				//for each setting
				this._define(a,coll[a]);		//set value through config
		}
	},
	//helper for object initialization
	_parseSettings:function(obj,initial){
		//initial - set of default values
		var settings = dhtmlx.extend({},initial);
		//code below will copy all properties over default one
		if (typeof obj == "object" && !obj.tagName)
			dhtmlx.extend(settings,obj);	
		//call config for each setting
		this._parseSeetingColl(settings);
	},
	_mergeSettings:function(config, defaults){
		for (var key in defaults)
			switch(typeof config[key]){
				case "object": 
					config[key] = this._mergeSettings((config[key]||{}), defaults[key]);
					break;
				case "undefined":
					config[key] = defaults[key];
					break;
				default:	//do nothing
					break;
			}
		return config;
	},
	//helper for html container init
	_parseContainer:function(obj,name,fallback){
		/*
			parameter can be a config object, in such case real container will be obj.container
			or it can be html object or ID of html object
		*/
		if (typeof obj == "object" && !obj.tagName) 
			obj=obj.container;
		this._obj = dhtmlx.toNode(obj);
		if (!this._obj && fallback)
			this._obj = fallback(obj);
			
		dhtmlx.assert(this._obj, "Incorrect html container");
		
		this._obj.className+=" "+name;
		this._obj.onselectstart=function(){return false;};	//block selection by default
		this._dataobj = this._obj;//separate reference for rendering modules
	},
	//apply template-type
	_set_type:function(name){
		//parameter can be a hash of settings
		if (typeof name == "object")
			return this.type_setter("type",name);
		
		dhtmlx.assert(this.types, "RenderStack :: Types are not defined");
		dhtmlx.assert(this.types[name],"RenderStack :: Inccorect type name",name);
		//or parameter can be a name of existing template-type	
		this.type=dhtmlx.extend({},this.types[name]);
		this.customize();	//init configs
	},
	customize:function(obj){
		//apply new properties
		if (obj) dhtmlx.extend(this.type,obj);
		
		//init tempaltes for item start and item end
		this.type._item_start = dhtmlx.Template.fromHTML(this.template_item_start(this.type));
		this.type._item_end = this.template_item_end(this.type);
		
		//repaint self
		this.render();
	},
	//config.type - creates new template-type, based on configuration object
	type_setter:function(mode,value){
		this._set_type(typeof value == "object"?dhtmlx.Type.add(this,value):value);
		return value;
	},
	//config.template - creates new template-type with defined template string
	template_setter:function(mode,value){
		return this.type_setter("type",{template:value});
	},
	//config.css - css name for top level container
	css_setter:function(mode,value){
		this._obj.className += " "+value;
		return value;
	}
};


/* DHX DEPEND FROM FILE 'compatibility.js'*/


/*
	Collection of compatibility hacks
*/

/*DHX:Depend dhtmlx.js*/

dhtmlx.compat=function(name, obj){
	//check if name hash present, and applies it when necessary
	if (dhtmlx.compat[name])
		dhtmlx.compat[name](obj);
};


(function(){
	if (!window.dhtmlxError){
		//dhtmlxcommon is not included
		
		//create fake error tracker for connectors
		var dummy = function(){};
		window.dhtmlxError={ catchError:dummy, throwError:dummy };
		//helpers instead of ones from dhtmlxcommon
		window.convertStringToBoolean=function(value){
			return !!value;
		};
		window.dhtmlxEventable = function(node){
			dhtmlx.extend(node,dhtmlx.EventSystem);
		};
		//imitate ajax layer of dhtmlxcommon
		var loader = {
			getXMLTopNode:function(name){
				
			},
			doXPath:function(path){
				return dhtmlx.DataDriver.xml.xpath(this.xml,path);
			},
			xmlDoc:{
				responseXML:true
			}
		};
		//wrap ajax methods of dataprocessor
		dhtmlx.compat.dataProcessor=function(obj){
			//FIXME
			//this is pretty ugly solution - we replace whole method , so changes in dataprocessor need to be reflected here
			
			var sendData = "_sendData";
			var in_progress = "_in_progress";
			var tMode = "_tMode";
			var waitMode = "_waitMode";
			
			obj[sendData]=function(a1,rowId){
		    	if (!a1) return; //nothing to send
		    	if (rowId)
					this[in_progress][rowId]=(new Date()).valueOf();
			    
				if (!this.callEvent("onBeforeDataSending",rowId?[rowId,this.getState(rowId)]:[])) return false;				
				
				var a2 = this;
		        var a3=this.serverProcessor;
				if (this[tMode]!="POST")
					//use dhtmlx.ajax instead of old ajax layer
					dhtmlx.ajax().get(a3+((a3.indexOf("?")!=-1)?"&":"?")+this.serialize(a1,rowId),"",function(t,x,xml){
						loader.xml = dhtmlx.DataDriver.xml.checkResponse(t,x);
						a2.afterUpdate(a2, null, null, null, loader);
					});
				else
		        	dhtmlx.ajax().post(a3,this.serialize(a1,rowId),function(t,x,xml){
		        		loader.xml = dhtmlx.DataDriver.xml.checkResponse(t,x);
		        		a2.afterUpdate(a2, null, null, null, loader);
		    		});
		
				this[waitMode]++;
		    };
		};
	}
	
})();


/* DHX DEPEND FROM FILE 'compatibility_layout.js'*/


/*DHX:Depend dhtmlx.js*/
/*DHX:Depend compatibility.js*/

if (!dhtmlx.attaches)
	dhtmlx.attaches = {};
	
dhtmlx.attaches.attachAbstract=function(name, conf){
	var obj = document.createElement("DIV");
	obj.id = "CustomObject_"+dhtmlx.uid();
	obj.style.width = "100%";
	obj.style.height = "100%";
	obj.cmp = "grid";
	document.body.appendChild(obj);
	this.attachObject(obj.id);
	
	conf.container = obj.id;
	
	var that = this.vs[this.av];
	that.grid = new window[name](conf);
	
	that.gridId = obj.id;
	that.gridObj = obj;
	
		
	that.grid.setSizes = function(){
		if (this.resize) this.resize();
		else this.render();
	};
	
	var method_name="_viewRestore";
	return this.vs[this[method_name]()].grid;
};
dhtmlx.attaches.attachDataView = function(conf){
	return this.attachAbstract("dhtmlXDataView",conf);
};
dhtmlx.attaches.attachChart = function(conf){
	return this.attachAbstract("dhtmlXChart",conf);
};

dhtmlx.compat.layout = function(){};



/* DHX DEPEND FROM FILE 'load.js'*/


/* 
	ajax operations 
	
	can be used for direct loading as
		dhtmlx.ajax(ulr, callback)
	or
		dhtmlx.ajax().get(url)
		dhtmlx.ajax().post(url)

*/

/*DHX:Depend datastore.js*/
/*DHX:Depend dhtmlx.js*/

dhtmlx.ajax = function(url,call,master){
	//if parameters was provided - made fast call
	if (arguments.length!==0){
		var http_request = new dhtmlx.ajax();
		if (master) http_request.master=master;
		http_request.get(url,null,call);
	}
	if (!this.getXHR) return new dhtmlx.ajax(); //allow to create new instance without direct new declaration
	
	return this;
};
dhtmlx.ajax.prototype={
	//creates xmlHTTP object
	getXHR:function(){
		if (dhtmlx._isIE)
		 return new ActiveXObject("Microsoft.xmlHTTP");
		else 
		 return new XMLHttpRequest();
	},
	/*
		send data to the server
		params - hash of properties which will be added to the url
		call - callback, can be an array of functions
	*/
	send:function(url,params,call){
		var x=this.getXHR();
		if (typeof call == "function")
		 call = [call];
		//add extra params to the url
		if (typeof params == "object"){
			var t=[];
			for (var a in params)
			 t.push(a+"="+encodeURIComponent(params[a]));// utf-8 escaping
			params=t.join("&");
		}
		if (params && !this.post){
			url=url+(url.indexOf("?")!=-1 ? "&" : "?")+params;
			params=null;
		}
		
		x.open(this.post?"POST":"GET",url,!this._sync);
		if (this.post)
		 x.setRequestHeader('Content-type','application/x-www-form-urlencoded');
		 
		//async mode, define loading callback
		if (!this._sync){
		 var self=this;
		 x.onreadystatechange= function(){
			if (!x.readyState || x.readyState == 4){
				dhtmlx.log_full_time("data_loading");	//log rendering time
				if (call && self) 
					for (var i=0; i < call.length; i++)	//there can be multiple callbacks
					 if (call[i])
						call[i].call((self.master||self),x.responseText,x.responseXML,x);
				self.master=null;
				call=x=self=null;	//anti-leak
			}
		 };
		}
		
		x.send(params||null);
		return x; //return XHR, which can be used in case of sync. mode
	},
	//GET request
	get:function(url,params,call){
		this.post=false;
		return this.send(url,params,call);
	},
	//POST request
	post:function(url,params,call){
		this.post=true;
		return this.send(url,params,call);
	}, 
	sync:function(){
		this._sync = true;
		return this;
	}
};


/*
	Behavior:DataLoader - load data in the component
	
	@export
		load
		parse
*/
dhtmlx.DataLoader={
	_init:function(){
		//prepare data store
		this.data = new dhtmlx.DataStore();
	},
	//loads data from external URL
	load:function(url,call){
		this.callEvent("onXLS",[]);
		if (typeof call == "string"){	//second parameter can be a loading type or callback
		 this.data.setDriver(call);
		 call = arguments[2];
		}
		//prepare data feed for dyn. loading
		if (!this.data.feed)
		 this.data.feed = function(from,count){
			//allow only single request at same time
			if (this._load_count)
				return this._load_count=[from,count];	//save last ignored request
			else
				this._load_count=true;
				
			this.load(url+((url.indexOf("?")==-1)?"?":"&")+"posStart="+from+"&count="+count,function(){
				//after loading check if we have some ignored requests
				var temp = this._load_count;
				this._load_count = false;
				if (typeof temp =="object")
					this.data.feed.apply(this, temp);	//load last ignored request
			});
		 };
		//load data by async ajax call
		dhtmlx.ajax(url,[this._onLoad,call],this);
	},
	//loads data from object
	parse:function(data,type){
		this.callEvent("onXLS",[]);
		if (type)
		 this.data.setDriver(type);
		this._onLoad(data,null);
	},
	//default after loading callback
	_onLoad:function(text,xml,loader){
		this.data._parse(this.data.driver.toObject(text,xml));
		this.callEvent("onXLE",[]);
	}
};

/*
	Abstraction layer for different data types
*/

dhtmlx.DataDriver={};
dhtmlx.DataDriver.json={
	//convert json string to json object if necessary
	toObject:function(data){
		if (typeof data == "string"){
		 eval ("dhtmlx.temp="+data);
		 return dhtmlx.temp;
		}
		return data;
	},
	//get array of records
	getRecords:function(data){
		if (data && !(data instanceof Array))
		 return [data];
		return data;
	},
	//get hash of properties for single record
	getDetails:function(data){
		return data;
	},
	//get count of data and position at which new data need to be inserted
	getInfo:function(data){
		return { 
		 _size:(data.total_count||0),
		 _from:(data.pos||0)
		};
	}
};

dhtmlx.DataDriver.html={
	/*
		incoming data can be
		 - collection of nodes
		 - ID of parent container
		 - HTML text
	*/
	toObject:function(data){
		if (typeof data == "string"){
		 var t=null;
		 if (data.indexOf("<")==-1)	//if no tags inside - probably its an ID
			t = dhtmlx.toNode(data);
		 if (!t){
			t=document.createElement("DIV");
			t.innerHTML = data;
		 }
		 
		 return t.getElementsByTagName(this.tag);
		}
		return data;
	},
	//get array of records
	getRecords:function(data){
		if (data.tagName)
		 return data.childNodes;
		return data;
	},
	//get hash of properties for single record
	getDetails:function(data){
		return dhtmlx.DataDriver.xml.tagToObject(data);
	},
	//dyn loading is not supported by HTML data source
	getInfo:function(data){
		return { 
		 _size:0,
		 _from:0
		};
	},
	tag: "LI"
};

dhtmlx.DataDriver.jsarray={
	//eval jsarray string to jsarray object if necessary
	toObject:function(data){
		if (typeof data == "string"){
		 eval ("dhtmlx.temp="+data);
		 return dhtmlx.temp;
		}
		return data;
	},
	//get array of records
	getRecords:function(data){
		return data;
	},
	//get hash of properties for single record, in case of array they will have names as "data{index}"
	getDetails:function(data){
		var result = {};
		for (var i=0; i < data.length; i++) 
		 result["data"+i]=data[i];
		 
		return result;
	},
	//dyn loading is not supported by js-array data source
	getInfo:function(data){
		return { 
		 _size:0,
		 _from:0
		};
	}
};

dhtmlx.DataDriver.csv={
	//incoming data always a string
	toObject:function(data){
		return data;
	},
	//get array of records
	getRecords:function(data){
		return data.split(this.row);
	},
	//get hash of properties for single record, data named as "data{index}"
	getDetails:function(data){
		data = this.stringToArray(data);
		var result = {};
		for (var i=0; i < data.length; i++) 
		 result["data"+i]=data[i];
		 
		return result;
	},
	//dyn loading is not supported by csv data source
	getInfo:function(data){
		return { 
		 _size:0,
		 _from:0
		};
	},
	//split string in array, takes string surrounding quotes in account
	stringToArray:function(data){
		data = data.split(this.cell);
		for (var i=0; i < data.length; i++)
		 data[i] = data[i].replace(/^[ \t\n\r]*(\"|)/g,"").replace(/(\"|)[ \t\n\r]*$/g,"");
		return data;
	},
	row:"\n",	//default row separator
	cell:","	//default cell separator
};

dhtmlx.DataDriver.xml={
	//convert xml string to xml object if necessary
	toObject:function(text,xml){
		if (xml && (xml=this.checkResponse(text,xml)))	//checkResponse - fix incorrect content type and extra whitespaces errors
		 return xml;
		if (typeof text == "string"){
		 return this.fromString(text);
		}
		return text;
	},
	//get array of records
	getRecords:function(data){
		return this.xpath(data,this.records);
	},
	records:"/*/item",
	userdata:"/*/userdata",
	//get hash of properties for single record
	getDetails:function(data){
		return this.tagToObject(data,{});
	},
	getUserData:function(data,col){
		col = col || {};
		var ud = this.xpath(data,this.userdata);
		for (var i=0; i < ud.length; i++) {
			var udx = this.tagToObject(ud[i]);
			col[udx.name] = udx.value;
		}
		return col;
	},
	//get count of data and position at which new data_loading need to be inserted
	getInfo:function(data){
		return { 
		 _size:(data.documentElement.getAttribute("total_count")||0),
		 _from:(data.documentElement.getAttribute("pos")||0)
		};
	},
	//xpath helper
	xpath:function(xml,path){
		if (window.XPathResult){	//FF, KHTML, Opera
		 var node=xml;
		 if(xml.nodeName.indexOf("document")==-1)
		 xml=xml.ownerDocument;
		 var res = [];
		 var col = xml.evaluate(path, node, null, XPathResult.ANY_TYPE, null);
		 var temp = col.iterateNext();
		 while (temp){ 
			res.push(temp);
			temp = col.iterateNext();
		}
		return res;
		}	//IE
		return xml.selectNodes(path);
	},
	//convert xml tag to js object, all subtags and attributes are mapped to the properties of result object
	tagToObject:function(tag,z){
		z=z||{};
		//map attributes
		var a=tag.attributes;
		for (var i=0; i<a.length; i++)
		 z[a[i].name]=a[i].value;
		//map subtags
		var flag=false;
		var b=tag.childNodes;
		var state = {};
		for (var i=0; i<b.length; i++){
			if (b[i].nodeType==1){
				var name = b[i].tagName;
				if (typeof z[name] != "undefined"){
					if (!(z[name] instanceof Array))
						z[name]=[z[name]];
					z[name].push(this.tagToObject(b[i],{}));
				}
				else
					z[b[i].tagName]=this.tagToObject(b[i],{});	//sub-object for complex subtags
				flag=true;
			}
		}
		
		if (!a.length && !flag)
			return this.nodeValue(tag);
		//each object will have its text content as "value" property
		z.value = this.nodeValue(tag);
		return z;
	},
	//get value of xml node 
	nodeValue:function(node){
		if (node.firstChild)
		 return node.firstChild.data;	//FIXME - long text nodes in FF not supported for now
		return "";
	},
	//convert XML string to XML object
	fromString:function(xmlString){
		if (window.DOMParser)		// FF, KHTML, Opera
		 return (new DOMParser()).parseFromString(xmlString,"text/xml");
		if (window.ActiveXObject){	// IE, utf-8 only 
		 temp=new ActiveXObject("Microsoft.xmlDOM");
		 temp.loadXML(xmlString);
		 return temp;
		}
		dhtmlx.error("Load from xml string is not supported");
	},
	//check is XML correct and try to reparse it if its invalid
	checkResponse:function(text,xml){ 
		if (xml && ( xml.firstChild && xml.firstChild.tagName != "parsererror") )
			return xml;
		//parsing as string resolves incorrect content type
		//regexp removes whitespaces before xml declaration, which is vital for FF
		var a=this.from_string(text.responseText.replace(/^[\s]+/,""));
		if (a) return a;
		
		dhtmlx.error("xml can't be parsed",text.responseText);
	}
};




/* DHX DEPEND FROM FILE 'compatibility_grid.js'*/


/*
	Compatibility hack for loading data from the grid.
	Provides new type of datasource - dhtmlxgrid
	
*/

/*DHX:Depend load.js*/

dhtmlx.DataDriver.dhtmlxgrid={
	_grid_getter:"_get_cell_value",
	toObject:function(data){
		this._grid = data;
		return data;
	},
	getRecords:function(data){
		return data.rowsBuffer;
	},
	getDetails:function(data){
		var result = {};
		for (var i=0; i < this._grid.getColumnsNum(); i++)
			result["data"+i]=this._grid[this._grid_getter](data,i);
      
		return result;
	},
	getInfo:function(data){
		return { 
			_size:0,
			_from:0
		};
	}
};


/* DHX DEPEND FROM FILE 'canvas.js'*/


/*DHX:Depend thirdparty\excanvas*/
/*DHX:Depend dhtmlx.js*/

dhtmlx.Canvas = {
	_init:function(){
		this._canvas_labels = [];
	},
	_prepareCanvas:function(container){
		//canvas has the same size as master object
		this._canvas = dhtmlx.html.create("canvas",{ width:container.offsetWidth, height:container.offsetHeight });
		container.appendChild(this._canvas);
		//use excanvas in IE
		if (!this._canvas.getContext){
			if (dhtmlx._isIE){
				dhtmlx.require("thirdparty/excanvas/excanvas.js");	//sync loading
				G_vmlCanvasManager.init_(document);
				G_vmlCanvasManager.initElement(this._canvas);
			} else	//some other not supported browser
				dhtmlx.error("Canvas is not supported in the current browser");
		}
		return this._canvas;
	}, 
	getCanvas:function(context){
		return (this._canvas||this._prepareCanvas(this._obj)).getContext(context||"2d");
	},
	_resizeCanvas:function(){
		if (this._canvas){
			this._canvas.setAttribute("width", this._canvas.parentNode.offsetWidth);
			this._canvas.setAttribute("height", this._canvas.parentNode.offsetHeight);
		}
	},
	renderText:function(x,y,text,css,w){
		if (!text) return; //ignore empty text
		
		var t = dhtmlx.html.create("DIV",{
			"class":"dhx_canvas_text"+(css?(" "+css):""),
			"style":"left:"+x+"px; top:"+y+"px;"
		},text);
		this._obj.appendChild(t);
		this._canvas_labels.push(t); //destructor?
		if (w)
			t.style.width = w+"px";
		return t;
	},
	renderTextAt:function(valign,align, x,y,t,c,w){
		var text=this.renderText.call(this,x,y,t,c,w);
		if (text){
			if (valign){
				if(valign == "middle")
					text.style.top = parseInt(y-text.offsetHeight/2,10) + "px";
				else
					text.style.top = y-text.offsetHeight + "px";
			}
			if (align){
			    if(align == "left")
					text.style.left = x-text.offsetWidth + "px";
				else
					text.style.left = parseInt(x-text.offsetWidth/2,10) + "px";
			}
		}
		return text;
	},
	clearCanvas:function(){
		for(var i=0; i < this._canvas_labels.length;i++)
			this._obj.removeChild(this._canvas_labels[i]);
		this._canvas_labels = [];
		if (this._obj._htmlmap){
			this._obj._htmlmap.parentNode.removeChild(this._obj._htmlmap);
			this._obj._htmlmap = null;
		}
		//FF breaks, when we are using clear canvas and call clearRect without parameters		
		this.getCanvas().clearRect(0,0,this._canvas.offsetWidth, this._canvas.offsetHeight);
	}
};


/* DHX INITIAL FILE 'D:\dev\xampp\htdocs\temp\chart\dhtmlxCore/sources//chart.js'*/


/*DHX:Depend chart.css*/
/*DHX:Depend canvas.js*/
/*DHX:Depend load.js*/

/*DHX:Depend compatibility_grid.js*/
/*DHX:Depend compatibility_layout.js*/

/*DHX:Depend config.js*/
/*DHX:Depend destructor.js*/
/*DHX:Depend mouse.js*/
/*DHX:Depend key.js*/
/*DHX:Depend group.js*/
/*DHX:Depend autotooltip.js*/

/*DHX:Depend ext/chart/chart_base.js*/
/*DHX:Depend ext/chart/chart_pie.js*/		//+pie3d
/*DHX:Depend ext/chart/chart_bar.js*/	
/*DHX:Depend ext/chart/chart_line.js*/
/*DHX:Depend ext/chart/chart_barh.js*/	
/*DHX:Depend ext/chart/chart_stackedbar.js*/	
/*DHX:Depend ext/chart/chart_stackedbarh.js*/
/*DHX:Depend ext/chart/chart_spline.js*/	
/*DHX:Depend ext/chart/chart_area.js*/	 	//+stackedArea

/*DHX:Depend math.js*/
/*DHX:Depend destructor.js*/
/*DHX:Depend dhtmlx.js*/


dhtmlXChart = function(container){
	this.name = "Chart";	
	this.version = "3.0";	
	
	if (dhtmlx.assert_enabled()) this._assert();
	
	dhtmlx.extend(this, dhtmlx.Settings);
	
	this._parseContainer(container,"dhx_chart");
	
	dhtmlx.extend(this, dhtmlx.DataLoader);
	this.data.provideApi(this,true);
	
	dhtmlx.extend(this, dhtmlx.EventSystem);
	dhtmlx.extend(this, dhtmlx.MouseEvents);
	dhtmlx.extend(this, dhtmlx.Destruction);
	dhtmlx.extend(this, dhtmlx.Canvas);
	dhtmlx.extend(this, dhtmlx.Group);
	dhtmlx.extend(this, dhtmlx.AutoTooltip);
	
	for (var key in dhtmlx.chart)
		dhtmlx.extend(this, dhtmlx.chart[key]);
	
	this._parseSettings(container,{
		color:"RAINBOW",
		alpha:"1",
		label:false,
		value:"{obj.value}",
		padding:{},
		view:"pie",
		lineColor:"#ffffff",
		cant:0.5,
		width: 15,
		labelWidth:100,
		line:{},
		item:{},
		shadow:true,
		gradient:false,
		border:true,
		labelOffset: 20,
		origin:"auto"
	});
	this._series = [this._settings];
	this.data.attachEvent("onStoreUpdated",dhtmlx.bind(function(){
		this.render();  
	},this));
	this.attachEvent("onLocateData", this._switchSerie);
};
dhtmlXChart.prototype={
	_id:"dhx_area_id",
	on_click:{
	},
	on_dblclick:{
	},
	on_mouse_move:{
	},
	resize:function(){
		this._resizeCanvas();
		this.render();	
	},
	view_setter:function(name, val){
		if (!dhtmlx.chart[val])
			dhtmlx.error("Chart type extension is not loaded: "+val);
		//if you will need to add more such settings - move them ( and this one ) in a separate methods
		
		if (typeof this._settings.offset == "undefined"){
			if (val == "area" || val == "stackedArea") 
				this._settings.offset = false;
			else
				this._settings.offset = true;
		}
			
			
		return val;
	},
	render:function(){
		if (!this.callEvent("onBeforeRender",[this.data]))
			return;
			
		this.clearCanvas();
		if(this._settings.legend){
			this._drawLegend(this.getCanvas(),
				this.data.getRange(),
				this._obj.offsetWidth,
				this._obj.offsetHeight
			);
		}
		var bounds = this._getChartBounds(this._obj.offsetWidth,this._obj.offsetHeight);
		var map = new dhtmlx.ui.Map(this._id);
		
		var temp = this._settings;
		for(var i=0; i < this._series.length;i++){
		 	this._settings = this._series[i];
			this["pvt_render_"+this._settings.view](
				this.getCanvas(),
				this.data.getRange(),
				bounds.start,
				bounds.end,
				i,
				map
			);
		}
		map.render(this._obj);
		this._settings = temp;
	},
	
	value_setter:dhtmlx.Template.obj_setter,	
	alpha_setter:dhtmlx.Template.obj_setter,	
	label_setter:dhtmlx.Template.obj_setter,
	lineColor_setter:dhtmlx.Template.obj_setter,	
	pieInnerText_setter:dhtmlx.Template.obj_setter,
	gradient_setter:function(name,config){
		if((typeof(config)!="function")&&config&&(config === true||config!="3d"))
			config = "light";
		return config;
	},
	colormap:{
		"RAINBOW":function(obj){
			var pos = Math.floor(this.indexById(obj.id)/this.dataCount()*1536);
			if (pos==1536) pos-=1;
			return this._rainbow[Math.floor(pos/256)](pos%256);
		}
	},
	color_setter:function(name, value){
		return this.colormap[value]||dhtmlx.Template.obj_setter(name, value);
	},
	legend_setter:function(name, config){	
		if(typeof(config)!="object")	//allow to use template string instead of object
			config={template:config};
			
		this._mergeSettings(config,{
			width:150,
			height:18,
			layout:"y",
			align:"left",
			valign:"bottom",
			template:"",
			marker:{
				type:"square",
				width:25,
				height:15
			}
		});
		
		config.template = dhtmlx.Template.setter(0,config.template);
		return config;
	},
	item_setter:function(name, config){
		if(typeof(config)!="object")
			config={color:config, borderColor:config};
			
		this._mergeSettings(config,{
			radius:4,
			color:"#000000",
			borderColor:"#000000",
			borderWidth:2
		});
		
		config.color = dhtmlx.Template.setter(0,config.color);
		config.borderColor = dhtmlx.Template.setter(0,config.borderColor);
		return config;
	},
	line_setter:function(name, config){
		if(typeof(config)!="object")
			config={color:config};
			
		this._mergeSettings(config,{
			width:3,
			color:"#d4d4d4"
		});
		
		config.color = dhtmlx.Template.setter(0,config.color);
		return config;
	},
	padding_setter:function(name, config){	
		if(typeof(config)!="object")
			config={left:config, right:config, top:config, bottom:config};
		this._mergeSettings(config,{
			left:50,
			right:20,
			top:35,
			bottom:40
		});
		return config;
	},
	xAxis_setter:function(name, config){
		if(!config) return false;
		if(typeof(config)!="object")
			config={ template:config };

		this._mergeSettings(config,{
			title:"",
			color:"#000000",
			template:"{obj}",
			lines:false
		});
		
		if(config.template)
			config.template = dhtmlx.Template.setter(0,config.template);
		return config;
	},
    yAxis_setter:function(name, config){
	    this._mergeSettings(config,{
			title:"",
			color:"#000000",
			template:"{obj}",
			lines:true
		});
		
		if(config.template)
			config.template = dhtmlx.Template.setter(0,config.template);
		return config;
	},
    _drawScales:function(ctx,data,point0,point1,start,end,cellWidth){
	    var y = this._drawYAxis(ctx,data,point0,point1,start,end);
		this._drawXAxis(ctx,data,point0,point1,cellWidth,y);
		return y;
	},
	_drawXAxis:function(ctx,data,point0,point1,cellWidth,y){
		if (!this._settings.xAxis) return;
		
		var x0 = point0.x-0.5;
		var y0 = parseInt((y?y:point1.y),10)+0.5;

		var x1 = point1.x;
		var unit_pos;
		var center = true;
		
		this._drawLine(ctx,x0,y0,x1,y0,this._settings.xAxis.color,1);
		
		for(var i=0; i < data.length;i ++){
			if(this._settings.offset === true)
				unit_pos = x0+cellWidth/2+i*cellWidth;
			else{
				unit_pos = x0+i*cellWidth;
				center = !!i;
			}
			/*scale labels*/
			var top = ((this._settings.origin!="auto")&&(this._settings.view=="bar")&&(parseFloat(this._settings.value(data[i]))<this._settings.origin));
			this._drawXAxisLabel(unit_pos,y0,data[i],center,top);
			/*draws a vertical line for the horizontal scale*/
			if(this._settings.view_setter != "bar")
		    	this._drawXAxisLine(ctx,unit_pos,point1.y,point0.y);
		}
		
		this.renderTextAt(true, false, x0,point1.y+this._settings.padding.bottom-3,
			this._settings.xAxis.title,
			"dhx_axis_title_x",
			point1.x - point0.x
		);
		
		/*the right border in lines in scale are enabled*/
		if (!this._settings.xAxis.lines || !this._settings.offset) return;
		this._drawLine(ctx,x1+0.5,point1.y,x1+0.5,point0.y+0.5,this._settings.xAxis.color,0.2);
	},
	_drawYAxis:function(ctx,data,point0,point1,start,end){
		var step;
		var scaleParam= {};
		if (!this._settings.yAxis) return;
		
		var x0 = point0.x - 0.5;
		var y0 = point1.y;
		var y1 = point0.y;
		var lineX = point1.y;
		
		this._drawLine(ctx,x0,y0,x0,y1,this._settings.yAxis.color,1);
		
		if(this._settings.yAxis.step)
		     step = parseFloat(this._settings.yAxis.step);

		if(typeof this._settings.yAxis.step =="undefined"||typeof this._settings.yAxis.start=="undefined"||typeof this._settings.yAxis.end =="undefined"){
			scaleParam = this._calculateScale(start,end);
			start = scaleParam.start;
			end = scaleParam.end;
			step = scaleParam.step;
			
			this._settings.yAxis.end = end;
			this._settings.yAxis.start = start;
		}
		
		if(step===0) return;
		var stepHeight = (y0-y1)*step/(end-start);
		var c = 0;
		for(var i = start; i<=end; i += step){
			if(scaleParam.fixNum)  i = parseFloat((new Number(i)).toFixed(scaleParam.fixNum));
			var yi = Math.floor(y0-c*stepHeight)+ 0.5;/*canvas line fix*/
			if(!(i==start&&this._settings.origin=="auto") &&this._settings.yAxis.lines)
				this._drawLine(ctx,x0,yi,point1.x,yi,this._settings.yAxis.color,0.2);
			if(i == this._settings.origin) lineX = yi;
			this.renderText(0,yi-5,
				this._settings.yAxis.template(i.toString()),
				"dhx_axis_item_y",
				point0.x-5
			);	
			c++;
		}
		this._setYAxisTitle(point0,point1);
		return lineX;
	},
	_setYAxisTitle:function(point0,point1){
		var text=this.renderTextAt("middle",false,0,parseInt((point1.y-point0.y)/2+point0.y,10),this._settings.yAxis.title,"dhx_axis_title_y");
		if (text)
			text.style.left = (dhtmlx.env.transform?(text.offsetHeight-text.offsetWidth)/2:0)+"px";
	},
	_calculateScale:function(nmin,nmax){
		var step,start,end;
	   	step = ((nmax-nmin)/8)||1;
		var power = Math.floor(this._log10(step));
		var calculStep = Math.pow(10,power);
		var stepVal = step/calculStep;
		stepVal = (stepVal>5?10:5);
		step = parseInt(stepVal,10)*calculStep;
		
		if(step>Math.abs(nmin))
			start = (nmin<0?-step:0);
		else{
			var absNmin = Math.abs(nmin);
			var powerStart = Math.floor(this._log10(absNmin));
			var nminVal = absNmin/Math.pow(10,powerStart);
			start = Math.ceil(nminVal*10)/10*Math.pow(10,powerStart)-step;
			if(nmin<0) start =-start-2*step;
		}
		var end = start;
		while(end<nmax){
			end += step;
			end = parseFloat((new Number(end)).toFixed(Math.abs(power)));
		}
		return { start:start,end:end,step:step,fixNum:Math.abs(power) };
	},
	_getLimits:function(orientation){
		var maxValue,minValue;
		var axis = ((arguments.length && orientation=="h")?this._settings.xAxis:this._settings.yAxis);
		if(axis&&(typeof axis.end!="undefied")&&(typeof axis.start!="undefied")&&axis.step){
		    maxValue = parseFloat(axis.end);
			minValue = parseFloat(axis.start);      
		}
		else{
			maxValue = this.max(this._series[0].value);
			minValue = this.min(this._series[0].value);
			if(this._series.length>1)
			for(var i=1; i < this._series.length;i++){
				var maxI = this.max(this._series[i].value);
				var minI = this.min(this._series[i].value);
				if (maxI > maxValue) maxValue = maxI;
		    	if (minI < minValue) minValue = minI;
			}
		}
		return {max:maxValue,min:minValue};
	},
	_log10:function(n){
        var method_name="log";
        return Math.floor((Math[method_name](n)/Math.LN10));
    },
	_drawXAxisLabel:function(x,y,obj,center,top){
		if (!this._settings.xAxis) return;
		var elem = this.renderTextAt(top, center, x,y,this._settings.xAxis.template(obj));
	},
	_drawXAxisLine:function(ctx,x,y1,y2){
		if (!this._settings.xAxis||!this._settings.xAxis.lines) return;
		this._drawLine(ctx,x,y1,x,y2,this._settings.xAxis.color,0.2);
	},
	_drawLine:function(ctx,x1,y1,x2,y2,color,width){
		ctx.strokeStyle = color;
		ctx.lineWidth = width;
		ctx.beginPath();
		ctx.moveTo(x1,y1);
		ctx.lineTo(x2,y2);
		ctx.stroke();
	},
	_getRelativeValue:function(minValue,maxValue){
	    var relValue;
		var valueFactor = 1;
		if(maxValue != minValue){
		    relValue = maxValue - minValue;
			if(Math.abs(relValue) < 1){
			    while(Math.abs(relValue)<1){
				    valueFactor *= 10;
					relValue *= valueFactor;
				}
			}
		}
		else relValue = minValue;
		return [relValue,valueFactor];
	},
	_rainbow : [
		function(pos){ return "#FF"+dhtmlx.math.toHex(pos/2,2)+"00";},
		function(pos){ return "#FF"+dhtmlx.math.toHex(pos/2+128,2)+"00";},
		function(pos){ return "#"+dhtmlx.math.toHex(255-pos,2)+"FF00";},
		function(pos){ return "#00FF"+dhtmlx.math.toHex(pos,2);},
		function(pos){ return "#00"+dhtmlx.math.toHex(255-pos,2)+"FF";},
		function(pos){ return "#"+dhtmlx.math.toHex(pos,2)+"00FF";}		
	],
	/**
	*   adds series to the chart (value and color properties)
	*   @param: obj - obj with configuration properties
	*/
	addSeries:function(obj){
		var temp = this._settings; this._settings = dhtmlx.extend({},temp);
		this._parseSettings(obj,{});
	    this._series.push(this._settings);
		this._settings = temp;
    },
    /*switch global settings to serit in question*/
    _switchSerie:function(id, tag){
    	this._active_serie = tag.getAttribute("userdata");
    	for (var i=0; i < this._series.length; i++) {
    		var tip = this._series[i].tooltip;
    		if (tip)
    			tip.disable();
		}
		var tip = this._series[this._active_serie].tooltip;
    	if (tip)
    		tip.enable();
    },
	/**
	*   renders legend block
	*   @param: ctx - canvas object
	*   @param: data - object those need to be displayed
	*   @param: width - the width of the container
	*   @param: height - the height of the container
	*/
	_drawLegend:function(ctx,data,width,height){
		/*position of the legend block*/
		var x=0,y=0;
		/*legend config*/
		var legend = this._settings.legend;
		 /*the legend sizes*/
		var legendHeight,legendWidth;
		
		var style = (this._settings.legend.layout!="x"?"width:"+legend.width+"px":"");
		/*creation of legend container*/
		var legendContainer = dhtmlx.html.create("DIV",{
			"class":"dhx_chart_legend",
			"style":"left:"+x+"px; top:"+y+"px;"+style
		},"");
		this._obj.appendChild(legendContainer);
		/*rendering legend text items*/
		var legendItems = [];
		if(!legend.values)
			for(var i = 0; i < data.length; i++){
				legendItems.push(this._drawLegendText(legendContainer,legend.template(data[i])));
			}
		else
			for(var i = 0; i < legend.values.length; i++){
				legendItems.push(this._drawLegendText(legendContainer,legend.values[i].text));
			}
	   	legendWidth = legendContainer.offsetWidth;
	    legendHeight = legendContainer.offsetHeight;
		this._settings.legend.width = legendWidth;
		this._settings.legend.height = legendHeight;
		/*setting legend position*/
		if(legendWidth<this._obj.offsetWidth){
			if(legend.layout == "x"&&legend.align == "center")
				x = (this._obj.offsetWidth-legendWidth)/2;
			if(legend.align == "right"){
				x = this._obj.offsetWidth-legendWidth;
			}
		}
		
		if(legendHeight<this._obj.offsetHeight){
			if(legend.valign == "middle"&&legend.align != "center"&&legend.layout != "x")
				y = (this._obj.offsetHeight-legendHeight)/2;
			else if(legend.valign == "bottom")
				y = this._obj.offsetHeight-legendHeight;
		}
		legendContainer.style.left = x+"px";
		legendContainer.style.top = y+"px";
		
		/*drawing colorful markers*/
		for(var i = 0; i < legendItems.length; i++){
			var item = legendItems[i];
			var itemColor = (legend.values?legend.values[i].color:this._settings.color.call(this,data[i]));
			this._drawLegendMarker(ctx,item.offsetLeft+x,item.offsetTop+y,itemColor);
		}
		legendItems = null;
	},
	/**
	*   appends legend item to legend block
	*   @param: ctx - canvas object
	*   @param: obj - data object that needs being represented
	*/
	_drawLegendText:function(cont,value){
		var style = "";
		if(this._settings.legend.layout=="x")
			style = "float:left;";
		/*the text of the legend item*/
		var text = dhtmlx.html.create("DIV",{
			"style":style+"padding-left:"+(10+this._settings.legend.marker.width)+"px",
			"class":"dhx_chart_legend_item"
		},value);
		cont.appendChild(text);
		return text;
	},
	/**
	*   draw legend colorful marder
	*   @param: ctx - canvas object
	*   @param: x - the horizontal position of the marker
	*   @param: y - the vertical position of the marker
	*   @param: obj - data object which color needs being used
	*/
	_drawLegendMarker:function(ctx,x,y,color){
		var details = this._settings.legend;
		
		ctx.strokeStyle = ctx.fillStyle = color;
		ctx.lineWidth = details.marker.height;  
		ctx.lineCap = details.marker.type;
		ctx.beginPath();
		/*start of marker*/
		x += ctx.lineWidth/2+5;
		y += ctx.lineWidth/2+3;
		ctx.moveTo(x,y);
		var x1 = x + details.marker.width-details.marker.height +1;
		ctx.lineTo(x1,y);  
    	ctx.stroke(); 
	},
	/**
	*   gets the points those represent chart left top and right bottom bounds
	*   @param: width - the width of the chart container
	*   @param: height - the height of the chart container
	*/
	_getChartBounds:function(width,height){
		var chartX0, chartY0, chartX1, chartY1;
		
		chartX0 = this._settings.padding.left;
		chartY0 = this._settings.padding.top;
		chartX1 = width - this._settings.padding.right;
		chartY1 = height - this._settings.padding.bottom;	
		
		if(this._settings.legend){
			var legend = this._settings.legend;
			/*legend size*/
			var legendWidth = this._settings.legend.width;
			var legendHeight = this._settings.legend.height;
		
			/*if legend is horizontal*/
			if(legend.layout == "x"){
				if(legend.valign == "center"){
					if(legend.align == "right")
						chartX1 -= legendWidth;
					else if(legend.align == "left")
				 		chartX0 += legendWidth;
			 	}
			 	else if(legend.valign == "bottom"){
			    	chartY1 -= legendHeight;
			 	}
			 	else{
			    	chartY0 += legendHeight;
			 	}
			}
			/*vertical scale*/
			else{
				if(legend.align == "right")
					chartX1 -= legendWidth;
			 	else if(legend.align == "left")
					chartX0 += legendWidth;
			}
		}
		return {start:{x:chartX0,y:chartY0},end:{x:chartX1,y:chartY1}};
	},
	/**
	*   gets the maximum and minimum values for the stacked chart
	*   @param: data - data set
	*/
	_getStackedLimits:function(data){
		var maxValue,minValue;
		if(this._settings.yAxis&&(typeof this._settings.yAxis.end!="undefied")&&(typeof this._settings.yAxis.start!="undefied")&&this._settings.yAxis.step){
		    maxValue = parseFloat(this._settings.yAxis.end);
			minValue = parseFloat(this._settings.yAxis.start);      
		}
		else{
			for(var i=0; i < data.length; i++){
				data[i].$sum = 0 ;
				data[i].$min = Infinity;
				for(var j =0; j < this._series.length;j++){
					var value = parseFloat(this._series[j].value(data[i]));
					if(isNaN(value)) continue;
					data[i].$sum += value;
					if(value < data[i].$min) data[i].$min = value;
				}
			}
			maxValue = -Infinity;
			minValue = Infinity;
			for(var i=0; i < data.length; i++){
				if (data[i].$sum > maxValue) maxValue = data[i].$sum ;
				if (data[i].$min < minValue) minValue = data[i].$min ;
			}
			if(minValue>0) minValue =0;
		}
		return {max:maxValue,min:minValue};
	},
	/*adds colors to the gradient object*/
	_setBarGradient:function(ctx,x1,y1,x2,y2,type,color,axis){
		var gradient,offset;
		if(type == "light"){
			if(axis == "x")
				gradient = ctx.createLinearGradient(x1,y1,x2,y1);
			else
				gradient = ctx.createLinearGradient(x1,y1,x1,y2);
			gradient.addColorStop(0,"#FFFFFF");
			gradient.addColorStop(0.9,color);
			gradient.addColorStop(1,color);
			offset = 2;
		}
		else{
			ctx.globalAlpha = 0.37;
			offset = 0;
			if(axis == "x")
				gradient = ctx.createLinearGradient(x1,y2,x1,y1);
			else
				gradient = ctx.createLinearGradient(x1,y1,x2,y1);
			gradient.addColorStop(0,"#000000");
			gradient.addColorStop(0.5,"#FFFFFF");
			gradient.addColorStop(0.6,"#FFFFFF");
			gradient.addColorStop(1,"#000000");
		}
		return {gradient:gradient,offset:offset};
	}
};

dhtmlx.compat("layout");
