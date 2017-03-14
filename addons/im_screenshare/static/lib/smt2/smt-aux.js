/*! 
 * (smt)2 simple mouse tracking v2.1.0
 * Copyleft (cc) 2006-2012 Luis Leiva
 * http://smt2.googlecode.com & http://smt.speedzinemedia.com
 */
/**
 * (smt)2 simple mouse tracking - auxiliary functions (smt-aux.js)
 * Copyleft (cc) 2006-2012 Luis Leiva
 * Release date: March 23 2012
 * http://smt2.googlecode.com & http://smt.speedzinemedia.com
 * @class smt2-aux
 * @version 2.1.0
 * @author Luis Leiva
 * @license Dual licensed under the MIT (MIT-LICENSE.txt) and GPL (GPL-LICENSE.txt) licenses.
 */

var smt2fn = {
  /**
   * Overrides (smt) tracking options object with custom-provided options object
   * @return void
   * @param {object} smtOptionsObj
   * @param {object} customOptionsObj
   * @see <code>smtOpt</code> object either in <code>smtRecord</code> or <code>smtReplay</code> classes
   */
  overrideTrackingOptions: function(smtOptionsObj, customOptionsObj)
  {
    for (var prop in smtOptionsObj)
    {
      if (customOptionsObj.hasOwnProperty(prop) && customOptionsObj[prop] !== null) {
        smtOptionsObj[prop] = customOptionsObj[prop];
      }
    }
  },
  
  /**
   * Allows recording/replaying the mouse path over Flash objects.
   * A Flash movie may display above all the layers on the HTML apge,
   * regardless of the stacking order ("z-index") of those layers.
   * Using a WMODE value of "opaque" or "transparent" will prevent a Flash movie from playing in the topmost layer
   * and allow you to adjust the layering of the movie within other layers of the HTML document.
   * However, to avoid possible performance issues, it's best use the "opaque" mode.
   * Note: The WMODE parameter is supported only on some browser/Flash Player version combinations.
   * If the WMODE parameter is not supported, the Flash movie will always display on top.
   * @param {Object}  d   document object   
   * @return void
   */
  allowTrackingOnFlashObjects: function(d)
  {
    var obj = d.getElementsByTagName("object");
    for (var i = 0, t = obj.length; i < t; ++i) {
      var param = d.createElement("param");
      param.setAttribute("name", "wmode");
      param.setAttribute("value","opaque");
      obj[i].appendChild(param);
    }

    var embed = d.getElementsByTagName("embed");
    for (var j = 0, u = embed.length; j < u; ++j) {
      embed[j].setAttribute("wmode", "opaque");
      // recording on some browsers is tricky (replaying is ok, though)
      if (!/MSIE/i.test(navigator.userAgent)) {
        /* Some browsers sets the wmode correctly,
         * but once the SWF object is instantiated you can't update its properties.
         * So, replace the old Flash object with the new one ;)
         */
        var cloned = embed[j].cloneNode(true);
        embed[j].parentNode.replaceChild(cloned, embed[j]);
      }
    }
  },
     
  /**
   * Traces any kind of objects in the debug console (if available).
   * @return void
   */
  log: function()
  {
    // check if console is available
    if (!window.console && !window.console.log) { return false; }
    // display messages in the console
    console.log(arguments);
  },
  
  /**
   * Checks the DOM-ready initialization in modern browsers.
   * This method was introduced by Dean Edwards/Matthias Miller/John Resig (dean.edwards.name/outofhanwell.com/jquery.com)
   * and it is discussed in http://dean.edwards.name/weblog/2006/06/again/
   * It's 2009, and fortunately nowadays there are only 2 types of modern browsers: W3C standards and Internet Explorer.
   * @return void
   * @param {function} callback   the function to be called on DOM load
   */
  onDOMload: function(callback)
  {
    if (arguments.callee.done) { return; }
    arguments.callee.done = true;

    // Firefox, Opera, Webkit-based browsers (Chrome, Safari)...
    if (document.addEventListener) {
      document.addEventListener('DOMContentLoaded', callback, false);
    }
    // Internet Explorer ¬¬
    else if (document.attachEvent) {
      try {
        document.write("<scr"+"ipt id=__ie_onload defer=true src=//:><\/scr"+"ipt>");
        var script = document.getElementById("__ie_onload");
        script.onreadystatechange = function() {
          if (this.readyState === 'complete') { callback(); }
        };
      } catch(err) {}
    }
    else {
      // fallback: old browsers use the window.onload event
      this.addEvent(window, 'load', callback);
    }
  },
  
  /**
   * Reloads the current page.
   * This method is needed for the drawing APIs,
   * where all window and screen data should be re-computed (and stage size should be reset).
   * @deprecated because IE's infinite loop behaviour
   * @return void
   */
  reloadPage: function()
  {
    // do not not alter the the browser's history
    window.location.replace(window.location.href);
  },
  
  /**
   * Loads more mouse trails for the current user, if available.
   * @return void
   * @param {object}   smtData    The user's data object
   */
  loadNextMouseTrail: function(smtData)
  {
    if (typeof smtData.api === 'undefined') { smtData.api = "js"; }
    var currTrailPos = this.array.indexOf(smtData.trails, smtData.currtrail);
    // check
    if (currTrailPos < smtData.trails.length - 1) {
      var navigateTo = smtData.trailurl+'?id='+smtData.trails[currTrailPos + 1]+'&api='+smtData.api;
      if (smtData.autoload) {
        window.location.href = navigateTo;
      } else if (confirm("This user also browsed more pages.\nDo you want to replay the next log?")) {
        window.location.href = navigateTo;
      }
    } else {
      alert("There are no more browsed pages for this user.");
    }
  },
  
  /**
   * Gets the position of element on page.
   * @autor Peter-Paul Koch (quirksMode.org)
   * @return {object} offset position - object with 2 properties: left {integer}, and top {integer}
   */
  findPos: function(obj)
  {
    var curleft = curtop = 0;
    if (obj && obj.offsetParent) {
      do {
  			curleft += obj.offsetLeft;
  			curtop  += obj.offsetTop;
      } while (obj = obj.offsetParent);
    }
    
    return { x:curleft, y:curtop };
  },
  
  /**
   * Gets the CSS styles of a DOM element.
   * @return {string} window dimmensions - object with 2 properties: width {integer}, and height {integer}
   */
  getStyle: function (oElm, strCssRule)
  {
  	var strValue = "";
  	//strCssRule = strCssRule.toLowerCase();
  	if(document.defaultView && document.defaultView.getComputedStyle){
  		strValue = document.defaultView.getComputedStyle(oElm, "").getPropertyValue(strCssRule);
  	}
  	else if(oElm.currentStyle) {
  		strCssRule = strCssRule.replace(/\-(\w)/g, function (strMatch, p1){
  			return p1.toUpperCase();
  		});
  		strValue = oElm.currentStyle[strCssRule];
  	}
  	
  	return strValue;
  },

  /**
   * Gets the browser's window size (aka 'the viewport').
   * @return {object} window dimmensions - object with 2 properties: width {integer}, and height {integer}
   */
  getWindowSize: function()
  {
    var d = document;
    var w = (window.innerWidth) ? window.innerWidth
            : (d.documentElement && d.documentElement.clientWidth) ? d.documentElement.clientWidth
            : (d.body && d.body.clientWidth) ? d.body.clientWidth
            : 0;
    var h = (window.innerHeight) ? window.innerHeight
            : (d.documentElement && d.documentElement.clientHeight) ? d.documentElement.clientHeight
            : (d.body && d.body.clientHeight) ? d.body.clientHeight
            : 0;
    return { width: w, height: h };
  },
  
  /**
   * Gets the browser window's offsets.
   * @return {object} window offsets - object with 2 properties: x {integer}, and y {integer}
   */
  getWindowOffset: function()
  {
    var d = document;
    var xpos = (window.pageXOffset) ? window.pageXOffset
                : (d.documentElement && d.documentElement.scrollLeft) ? d.documentElement.scrollLeft
                : (d.body && d.body.scrollLeft) ? d.body.scrollLeft
                : 0;
    var ypos = (window.pageYOffset) ? window.pageYOffset
                : (d.documentElement && d.documentElement.scrollTop) ? d.documentElement.scrollTop
                : (d.body && d.body.scrollTop) ? d.body.scrollTop
                : 0;

    return { x: xpos, y: ypos };
  },
  
  /**
   * Gets the document's size.
   * @return {object} document dimensions - object with 2 properties: width {integer}, and height {integer}
   */
  getDocumentSize: function()
  {
    var d = document;
    var w = (window.innerWidth && window.scrollMaxX) ? window.innerWidth + window.scrollMaxX
            : (d.body && d.body.scrollWidth > d.body.offsetWidth) ? d.body.scrollWidth
            : (d.body && d.body.offsetWidth) ? d.body.offsetWidth
            : 0;
    var h = (window.innerHeight && window.scrollMaxY) ? window.innerHeight + window.scrollMaxY
            : (d.body && d.body.scrollHeight > d.body.offsetHeight) ? d.body.scrollHeight
            : (d.body && d.body.offsetHeight) ? d.body.offsetHeight
            : 0;

    return { width: w, height: h };
  },
  
  /**
   * Gets the max value from both window (viewport's size) and document's size.
   * @return {object} viewport dimensions - object with 2 properties: width {integer}, and height {integer}
   */
  getPageSize: function()
  {
    var win = this.getWindowSize(),
        doc = this.getDocumentSize();

    // find max values from this group
    var w = (doc.width < win.width) ? win.width : doc.width;
    var h = (doc.height < win.height) ? win.height : doc.height;

    return { width: w, height: h };
  },
  
  /**
   * Gets the max z-index level available on the page.
   * @return {integer}    z-index level
   * @param {object} e    DOM element (default: document)
   * @autor Jason J. Jaeger (greengeckodesign.com)
   */
  getNextHighestDepth: function(e)
  {
    var highestIndex = 0;
    var currentIndex = 0;
    var elementArray = [];
    // check all elements in page ...
    if (document.getElementsByTagName) {
      elementArray = document.getElementsByTagName('*');
    } else if (e.getElementsByTagName) {
      elementArray = document.getElementsByTagName('*');
    }
    // ... and iterate
    for (var i = 0, l = elementArray.length; i < l; ++i) {
      if (elementArray[i].currentStyle) {
        currentIndex = parseFloat(elementArray[i].currentStyle.zIndex);
      } else if (window.getComputedStyle) {
        currentIndex = parseFloat(document.defaultView.getComputedStyle(elementArray[i],null).getPropertyValue('z-index'));
      }
      if (currentIndex > highestIndex) { highestIndex = currentIndex; }
    }

    return highestIndex + 1;
  },
  
  /**
   * Gets the base path of the current window location.
   * @return {string}    path
   */
  getBaseURL: function()
  {
    var basepath = window.location.href;
    var dirs = basepath.split("/");
    delete dirs[ dirs.length - 1 ];

    return dirs.join("/");
  },
  
  /**
   * Checks that a URL ends with a slash; otherwise it will be appended at the end of the URL.
   * @return {string}    url
   */  
  ensureLastURLSlash: function(url) 
  {
    if (url.lastIndexOf("/") != url.length - 1) {
      url += "/";
    }

    return url;
  },
  
  /**
   * Adds event listeners unobtrusively.
   * @return void
   * @param {object}    obj   Object to add listener(s) to
   * @param {string}    type  Event type
   * @param {function}  fn    Function to execute
   * @autor John Resig (jquery.com)
   */
  addEvent: function(obj, type, fn)
  {
    if (obj.addEventListener) {
      obj.addEventListener(type, fn, false);
    } else if (obj.attachEvent)	{
      obj["e"+type+fn] = fn;
      obj[type+fn] = function(){ obj["e"+type+fn](window.event); };
      obj.attachEvent("on"+type, obj[type+fn]);
    }
  },
  
  /**
   * Rounds a number to a given digits accuracy.
   * @return {float}
   * @param {float}   number  input number
   * @param {integer} digits  precision digits
   */
  roundTo: function(number,digits)
  {
    if (!digits) { digits = 2; }
    var exp = 100; // faster, because smt2 precision is the same for all computations!
    /* in 'taliban mode' that would be ok:
     * <code>var exp = Math.pow(10,digits);</code>
     * or even this, avoiding the pow function:
     * <code>for (var i = 0, exp = 1; i < digits.length; ++i, exp *= 10) {}</code>
     */
    return Math.round(exp*number)/exp;
  },
  
  /**
   * Scrolls the browser window.
   * This function is quite useful for replaying the user trails comfortably ;)
   * @return void
   * @param {object}   obj    Config object
   * @config {integer} xpos   X coordinate
   * @config {integer} ypos   Y coordinate
   * @config {integer} width  Viewport width
   * @config {integer} height Viewport height
   */
  doScroll: function(obj)
  {
    var off = this.getWindowOffset();
    // center current mouse coords on the viewport
    var xto = Math.round(obj.xpos - obj.width) + obj.width/2;
    var yto = Math.round(obj.ypos - obj.height) + obj.height/2;
    window.scrollBy(xto - off.x, yto - off.y);
  },
  
  /**
   * Creates an XML/HTTP request to provide async communication with the server.
   * @return {object} XHR object
   * @autor Peter-Paul Koch (quirksMode.org)
   */
  createXMLHTTPObject: function()
  {
    var xmlhttp = false;
    // current AJAX flavours
    var XMLHttpFactories = [
      function(){ return new XMLHttpRequest(); },
      function(){ return new ActiveXObject("Msxml2.XMLHTTP"); },
      function(){ return new ActiveXObject("Msxml3.XMLHTTP"); },
      function(){ return new ActiveXObject("Microsoft.XMLHTTP"); }
    ];
    // check AJAX flavour
    for (var i = 0; i < XMLHttpFactories.length; ++i) {
      try {
        xmlhttp = XMLHttpFactories[i]();
      } catch(err) { continue; }
      break;
    }

    return xmlhttp;
  },
  
  /**
   * Makes an asynchronous XMLHTTP request (XHR) via GET or POST.
   * Inspired on Peter-Paul Koch's XMLHttpRequest function.
   * @return void
   * @param  {object}    setup      Request properties
   * @config {string}    url        Request URL
   * @config {function} [callback]  Response function
   * @config {string}   [postdata]  POST vars in the form "var1=name&var2=name..."
   * @config {object}   [xmlhttp]   A previous XMLHTTP object can be reused
   */
  sendAjaxRequest: function(setup)
  {
    // create XHR object (or reuse it)
    var request = (setup.xmlhttp) ? setup.xmlhttp : this.createXMLHTTPObject();
    if (!request) { return; }

    var method = (setup.postdata) ? "POST" : "GET";
    // start request
    request.open(method, setup.url, true);
    // post requests must set the correct content type
    if (setup.postdata) {
      request.setRequestHeader('Content-Type', "application/x-www-form-urlencoded");
    }
    // check for the 'complete' request state
    request.onreadystatechange = function(){
      if (request.readyState == 4 && typeof setup.callback === 'function') {
        // send server response to callback function
        setup.callback(request.responseText);
      }
    };
    // send request
    request.send(setup.postdata);
  },
  
  /**
   * Cookies management object.
   * This cookies object allows you to store and retrieve cookies easily.
   * Cookies can be picked up by any other web pages in the correct domain.
   * Cookies are set to expire after a certain length of time.
   */
  cookies: {
    /**
     * Stores a cookie variable.
     * @return void
     * @param {string} name
     * @param {mixed}  value
     * @param {string} expiredays (optional) default: no expire
     * @param {string} domainpath (optional) default: root domain
     */
    setCookie: function(name,value,expiredays,domainpath)
    {
      var path = domainpath || "/";
      var expires = "";
      if (expiredays) {
        var date = new Date();
        date.setTime(date.getTime() + (expiredays*24*60*60*1000)); // ms
        expires = "; expires=" + date.toGMTString();
      }
      document.cookie = name +"="+ escape(value) + expires +"; path=" + path;
    },
    /**
     * Retrieves a cookie variable.
     * @return {string}       cookie value, or false on failure
     * @param {string} name   cookie name
     */
    getCookie: function(name)
    {
      var cStart,cEnd;
      if (document.cookie.length > 0) {
        cStart = document.cookie.indexOf(name+"=");
        if (cStart != -1) {
          cStart = cStart + name.length + 1;
          cEnd   = document.cookie.indexOf(";", cStart);
          if (cEnd == -1) {
            cEnd = document.cookie.length;
          }

          return unescape(document.cookie.substring(cStart, cEnd));
        }
      }
      return false;
    },
    /**
     * Checks if a cookie exists.
     * @return {boolean}       true on success, or false on failure
     * @param {string}  name   cookie name
     */
    checkCookie: function(name)
    {
      var c = this.getCookie(name);
      return (c);
    },
    /**
     * Deletes a cookie.
     * @param {string}  name   cookie name
     */
    deleteCookie: function(name)
    {
      if (this.checkCookie(name)) {
        this.setCookie(name, null, -1);
      }
    }
  },
  
  /**
   * Core for tracking widgets.
   * The word "widget" stands for *any* DOM element on the page.
   * This snippet was developed years ago as 'DOM4CSS', and now lives in harmony with smt2.
   */
  widget: {
    /**
     * Concatenation token.
     */  
    chainer: ">",
    /**
     * Finds the first available element with an ID.
     * Traversing count starts from current element to node parents.
     * This function should be registered on mouse move/down events.
     * @return {object}            DOM node element
     * @param {object}   e         DOM event
     * @param {function} callback  response function
     */
    findDOMElement: function(e,callback)
    {
      if (!e) { e = window.event; }
      // find the element
      var t = e.target || e.srcElement;
      // defeat Safari bug
      if (t.nodeType == 3) { t = t.parentNode; }
      // if the element has no ID, travese the DOM in reverse (find its parents)
      var check = (t.id) ? this.getID(t) : this.getParents(t);
      if (check) {
        callback(check);
      }
    },
    /**
     * Gets the element's id.
     * @return {string}     DOM node ID
     * @param {object}  o   DOM node element
     */
    getID: function(o)
    {
      // save HTML and BODY nodes?
      //if (o.nodeName == 'HTML' || o.nodeName == 'BODY') { return false; }
      
      return o.nodeName + "#" + o.id;
    },
    /**
     * Gets the element's class.
     * If that element has more than one CSS class, return only the first class name found.
     * @return {string}     DOM node class
     * @param {object}  o   DOM node element
     */
    getClass: function(o)
    {
      // save HTML and BODY nodes?
      //if (o.nodeName == 'HTML' || o.nodeName == 'BODY') { return false; }
      
      // if the element has no class, return its node name only
      return (o.className) ? o.nodeName + "." + o.className.split(" ")[0] : o.nodeName;
    },
    /**
     * Gets all node parents until a node with ID is found.
     * @return {string}     CSS selector string (intended to use in other scripts).
     * @param {object}  o   DOM node element
     */
    getParents: function(o)
    {
      // store current node first
      var elem = (o.id) ? this.getID(o) : this.getClass(o);
      var list = (elem) ? [elem] : [];
      // get all parents until find an element with ID
      while (o.parentNode)
      {
        o = o.parentNode;
        // store only element nodes
        if (o.nodeType == 1)
        {
          if (o.id) {
            elem = this.getID(o);
            list.unshift(elem);
            // if parent has an ID, end finding
            return list.join(this.chainer);
          } else {
            elem = this.getClass(o);
            list.unshift(elem);
          }
          if (o == parent) {
            // #document reached
            return list.join(this.chainer);
          }
        }
      }
      return list.join(this.chainer);
    }
  },
  
  /**
   * Array methods -- without extending the Array prototype (best practice).
   * Note: These Array methods would only work for a completely 'dense' array.
   * If you're working with sparse arrays, then you should pre-process them:
   * <code>
   *   var narray = [];
   *   for (var i = 0; i < array.length; ++i) {
   *     if (array[i] != null) { narray.push(array[i]); }
   *   }
   *   // now narray is converted to a 'dense' array
   * </code>
   */
  array: {
    /**
     * Gets the max element in a numeric array.
     * @return {float}        array max value
     * @param {array} array
     * @author John Resig
     */
    max: function(arr)
    {
      return Math.max.apply(Math, arr);
    },
    /**
     * Gets the min element in a numeric array.
     * @return {float}        array min value
     * @param {array} array
     * @author John Resig
     */
    min: function(arr)
    {
      return Math.max.apply(Math, arr);
    },
    /**
     * Sums all elements in a numeric array.
     * @return {float}        array sum
     * @param {array} arr
     */
    sum: function(arr)
    {
      var s = 0;
      for (var i = 0, l = arr.length; i < l; ++i) {
        s += arr[i];
      }
      return s;
    },
    /**
     * Appends any supplied arguments to the end of the array, in the order given.
     * @return {integer}        new length of the array
     * @param {array} arr
     * @param {mixed} content   anything to push to array
     * @author Ash Searle (tweaked by Luis Leiva)
     * @link http://hexmen.com/blog/
     * @license http://creativecommons.org/licenses/by/2.5/
     */
    push: function(arr, content)
    {
      var args = Array.prototype.slice.call(content);
      var n = arr.length >>> 0;
      for (var i = 0; i < args.length; ++i) {
        arr[n] = args[i];
        n = n + 1 >>> 0;
      }
      arr.length = n;
      return n;
    },
    /**
     * Removes the last element of the array and returns it.
     * @return {mixed}        element removed (if any). Otherwise return <code>undefined</code>
     * @param {array} arr
     * @author Ash Searle
     * @link http://hexmen.com/blog/
     * @license http://creativecommons.org/licenses/by/2.5/
     */
    pop: function(arr)
    {
      var n = arr.length >>> 0, value;
      if (n) {
        value = arr[--n];
        delete arr[n];
      }
      arr.length = n;
      return value;
    },
    /**
     * Removes element(s) in desired position(s) from input array and returns the modified array.
     * @return {array}          modified array
     * @param {array}   arr
     * @param {integer} from    start index
     * @param {integer} to      end index
     * @author John Resig
     */
    remove: function(arr, from, to)
    {
      var rest = arr.slice((to || from) + 1 || arr.length);
      arr.length = (from < 0) ? arr.length + from : from;
      return array.push.apply(arr, rest);
		},
    /**
     * Gets the index of the first element that matches search value.
     * @return {integer}          index if found, or -1 otherwise
     * @param {array}   arr
     * @param {mixed}   search    element to search for
     * @param {integer} from      start index
     * @link http://snipplr.com/view/3355/arrayindexof/
     */
    indexOf: function(arr, search, from)
    {
      for (var i = (from || 0), total = arr.length; i < total; ++i) {
        // strict types should use === comparison
        if (arr[i] == search) {
          return i;
        }
      }
      return -1;
    }
  }

};
