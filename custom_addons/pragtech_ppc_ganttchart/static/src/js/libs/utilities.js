/*
 Copyright (c) 2012-2017 Open Lab
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */



// works also for IE8 beta
var isExplorer = navigator.userAgent.toUpperCase().indexOf("MSIE") >= 0 || !!navigator.userAgent.match(/Trident.*rv\:11\./);
var isMozilla = navigator.userAgent.toUpperCase().indexOf("FIREFOX") >= 0;
var isSafari = navigator.userAgent.toLowerCase().indexOf("safari") != -1 && navigator.userAgent.toLowerCase().indexOf('chrome') < 0;

//Version detection
var version = navigator.appVersion.substring(0, 1);
var inProduction = false;
if (inProduction) {
  window.console = undefined;
}

// deprecated use $("#domid")...
function obj(element) {
	if (arguments.length > 1) {
		alert("invalid use of obj with multiple params:" + element)
	}
	var el = document.getElementById(element);
	if (!el)
		console.error("element not found: " + element);
	return el;
}

if (!window.console) {
	window.console = new function () {
		this.log = function (str) {/*alert(str)*/};
		this.debug = function (str) {/*alert(str)*/};
		this.error = function (str) {/*alert(str)*/};
	};
}
if (!window.console.debug || !window.console.error || !window.console.log) {
	window.console = new function () {
		this.log = function (str) {/*alert(str)*/};
		this.debug = function (str) {/*alert(str)*/};
		this.error = function (str) {/*alert(str)*/};
	};
}



String.prototype.trim = function () {
	return this.replace(/^\s*(\S*(\s+\S+)*)\s*$/, "$1");
};

String.prototype.startsWith = function (t, i) {
	if (!i) {
		return (t == this.substring(0, t.length));
	} else {
		return (t.toLowerCase() == this.substring(0, t.length).toLowerCase());
	}
};

String.prototype.endsWith = function (t, i) {
	if (!i) {
		return (t == this.substring(this.length - t.length));
	} else {
		return (t.toLowerCase() == this.substring(this.length - t.length).toLowerCase());
	}
};

// leaves only char from A to Z, numbers, _ -> valid ID
String.prototype.asId = function () {
	return this.replace(/[^a-zA-Z0-9_]+/g, '');
};

String.prototype.replaceAll = function (from, to) {
	return this.replace(new RegExp(RegExp.quote(from), 'g'), to);
};


if (!Array.prototype.indexOf) {
	Array.prototype.indexOf = function (searchElement, fromIndex) {
		if (this == null) {
			throw new TypeError();
		}
		var t = Object(this);
		var len = t.length >>> 0;
		if (len === 0) {
			return -1;
		}
		var n = 0;
		if (arguments.length > 0) {
			n = Number(arguments[1]);
			if (n != n) { // shortcut for verifying if it's NaN
				n = 0;
			} else if (n != 0 && n != Infinity && n != -Infinity) {
				n = (n > 0 || -1) * Math.floor(Math.abs(n));
			}
		}
		if (n >= len) {
			return -1;
		}
		var k = n >= 0 ? n : Math.max(len - Math.abs(n), 0);
		for (; k < len; k++) {
			if (k in t && t[k] === searchElement) {
				return k;
			}
		}
		return -1;
	};
}


Object.size = function (obj) {
	var size = 0, key;
	for (key in obj) {
		if (obj.hasOwnProperty(key)) size++;
	}
	return size;
};


// transform string values to printable: \n in <br>
function transformToPrintable(data) {
	for (var prop in data) {
		var value = data[prop];
		if (typeof(value) == "string")
			data[prop] = (value + "").replace(/\n/g, "<br>");
	}
	return data;
}


RegExp.quote = function (str) {
	return str.replace(/([.?*+^$[\]\\(){}-])/g, "\\$1");
};


/* Object Functions */

function stopBubble(e) {
	e.stopPropagation();
	e.preventDefault();
	return false;
}


// ------ ------- -------- wraps http://www.mysite.com/.......   with <a href="...">
jQuery.fn.activateLinks = function (showImages) {
	var httpRE = /(['"]\s*)?(http[s]?:[\d]*\/\/[^"<>\s]*)/g;
	var wwwRE = /(['"/]\s*)?(www\.[^"<>\s]+)/g;
	var imgRE = /(['"]\s*)?(http[s]?:[\d]*\/\/[^"<>\s]*\.(?:gif|jpg|png|jpeg|bmp))/g;


	this.each(function () {
		var el = $(this);
		var html = el.html();

		if (showImages) {
			// workaround for negative look ahead
			html = html.replace(imgRE, function ($0, $1) {
				return $1 ? $0 : "<div class='imgWrap'  onclick=\"window.open('" + $0 + "','_blank');event.stopPropagation();\"><img src='" + $0 + "' title='" + $0 + "'></div>";
			});
		}

		html = html.replace(httpRE, function ($0, $1) {
			return $1 ? $0 : "<a href='#' onclick=\"window.open('" + $0 + "','_blank');event.stopPropagation();\">" + $0 + "</a>";
		});

		html = html.replace(wwwRE, function ($0, $1) {
			return $1 ? $0 : "<a href='#' onclick=\"window.open('http://" + $0 + "','_blank');event.stopPropagation();\">" + $0 + "</a>";
		});

		el.empty().append(html);

		if (showImages) {
			//inject expand capability on images
			el.find("div.imgWrap").each(function () {
				var imageDiv = $(this);


				imageDiv.click(function (e) {
					if (e.ctrlKey || e.metaKey) {
						window.open(imageDiv.find("img").prop("src"), "_blank");
					} else {
						var imageClone = imageDiv.find("img").clone();
						imageClone.mouseout(function () {
							$(this).remove();
						});
						imageClone.addClass("imageClone").css({"position":"absolute", "display":"none", "top":imageDiv.position().top, "left":imageDiv.position().left, "z-index":1000000});
						imageDiv.after(imageClone);
						imageClone.fadeIn();
					}
				});
			});
		}

	});
	return this;
};

jQuery.fn.emoticonize = function () {
	function convert(text) {
		var faccRE = /(:\))|(:-\))|(:-])|(:-\()|(:\()|(:-\/)|(:-\\)|(:-\|)|(;-\))|(:-D)|(:-P)|(:-p)|(:-0)|(:-o)|(:-O)|(:'-\()|(\(@\))/g;
		return text.replace(faccRE, function (str) {
			var ret = {":)":"smile",
				":-)":"smile",
				":-]":"polite_smile",
				":-(":"frown",
				":(":"frown",
				":-/":"skepticism",
				":-\\":"skepticism",
				":-|":"sarcasm",
				";-)":"wink",
				":-D":"grin",
				":-P":"tongue",
				":-p":"tongue",
				":-o":"surprise",
				":-O":"surprise",
				":-0":"surprise",
				":'-(":"tear",
				"(@)":"angry"}[str];
			if (ret) {
				ret = "<img src='" + contextPath + "/img/smiley/" + ret + ".png' align='absmiddle'>";
				return ret;
			} else
				return str;
		});
	}

	function addBold(text) {
		var returnedValue;
		var faccRE = /\*\*[^*]*\*\*/ig;
		return text.replace(faccRE, function (str) {
			var temp = str.substr(2);
			var temp2 = temp.substr(0, temp.length - 2);
			return "<b>" + temp2 + "</b>";
		});
	}

	this.each(function () {
		var el = $(this);
		var html = convert(el.html());
		html = addBold(html);
		el.html(html);
	});
	return this;
};


$.fn.unselectable = function () {
	this.each(function () {
		$(this).addClass("unselectable").attr("unselectable", "on");
	});
	return $(this);
};

$.fn.clearUnselectable = function () {
	this.each(function () {
		$(this).removeClass("unselectable").removeAttr("unselectable");
	});
	return $(this);
};

// ---------------------------------- initialize management
var __initedComponents = new Object();

function initialize(url, type, ndo) {
  //console.debug("initialize before: " + url);
  var normUrl = url.asId();
  var deferred = $.Deferred();

  if (!__initedComponents[normUrl]) {
    __initedComponents[normUrl] = deferred;

    if ("CSS" == (type + "").toUpperCase()) {
      var link = $("<link rel='stylesheet' type='text/css'>").prop("href", url);
      $("head").append(link);
      deferred.resolve();

    } else if ("SCRIPT" == (type + "").toUpperCase()) {
      $.ajax({type: "GET",
        url:        url + "?" + buildNumber,
        dataType:   "script",
        cache:      true,
        success:    function () {
          //console.debug("initialize loaded:" + url);
          deferred.resolve()
        },
        error:      function () {
          //console.debug("initialize failed:" + url);
          deferred.reject();
        }
      });


    } else {
      //console.debug(url+" as DOM");
      //var text = getContent(url);
      url = url + (url.indexOf("?") > -1 ? "&" : "?") + buildNumber;
      var text = $.ajax({
        type:     "GET",
        url:      url,
        dataType: "html",
        cache:    true,
        success:  function (text) {
          //console.debug("initialize loaded:" + url);
          ndo = ndo || $("body");
          ndo.append(text);
          deferred.resolve()
        },
        error:    function () {
          //console.debug("initialize failed:" + url);
          deferred.reject();
        }
      });
    }
  }

  return __initedComponents[normUrl].promise();
}


/**
 *  callback receive event, data
 *  data.response  contiene la response json arrivata dal controller
 *  E.G.:
 *     $("body").trigger("worklogEvent",[{type:"delete",response:response}])
 *
 *     in caso di delete di solito c'è il response.deletedId
 */
function registerEvent(eventName,callback) {
  $("body").off(eventName).on(eventName, callback);
}


function openPersistentFile(file) {
  //console.debug("openPersistentFile",file);
  var t=window.self;
  try{
    if(window.top != window.self)
      t=window.top;
  } catch(e) {}

  if (file.mime.indexOf("image") >= 0) {
    var img = $("<img>").prop("src", file.url).css({position: "absolute", top: "-10000px", left: "-10000px"}).one("load", function () {
      //console.debug("image loaded");
      var img = $(this);
      var w = img.width();
      var h = img.height();
      //console.debug("image loaded",w,h);
      var f=w/h;
      var ww = $(t).width()*.8;
      var wh = $(t).height()*.8;
      if (w>ww){
        w=ww;
        h=w/f;
      }
      if (h>wh){
        h=wh;
        w=h*f;
      }

      var hasTop=false;
      img.width(w).height(h).css({position: "static", top: 0, left: 0});

      t.createModalPopup(w+100,h+100).append(img);
    });
    t.$("body").append(img);
  } else if (file.mime.indexOf("pdf") >= 0) {
    t.openBlackPopup(file.url, $(t).width()*.8, $(t).height()*.8);
	} else {
		window.open(file.url + "&TREATASATTACH=yes");
	}
}


function wrappedEvaluer(toEval){
  eval(toEval);
}

function evalInContext(stringToEval,context){
  wrappedEvaluer.apply(context,[stringToEval]);
}


Storage.prototype.setObject = function(key, value) {
  this.setItem(key, JSON.stringify(value));
};

Storage.prototype.getObject = function(key) {
  return this.getItem(key) && JSON.parse(this.getItem(key));
};

function objectSize(size) {
  var divisor = 1;
  var unit = "bytes";
  if (size >= 1024 * 1024) {
    divisor = 1024 * 1024;
    unit = "MB";
  } else if (size >= 1024) {
    divisor = 1024;
    unit = "KB";
  }
  if (divisor == 1)
    return size + " " + unit;

  return (size / divisor).toFixed(2) + ' ' + unit;
}


function htmlEncode(value){
  //create a in-memory div, set it's inner text(which jQuery automatically encodes)
  //then grab the encoded contents back out.  The div never exists on the page.
  return $('<div/>').text(value).html();
}

function htmlLinearize(value, length){
	value = value.replace(/(\r\n|\n|\r)/gm,"").replace(/<br>/g, " - ");
	value = value.replace(/-  -/g, "-");

	var ret = $('<div/>').text(value).text();

	if(length){
		var ellips = ret.length > length ? "..." : "";
		ret = ret.substring(0,length) + ellips;
	}

  return ret;
}

function htmlDecode(value){
  return $('<div/>').html(value).text();
}



function createCookie(name,value,days) {
	if (days) {
		var date = new Date();
		date.setTime(date.getTime()+(days*24*60*60*1000));
		var expires = "; expires="+date.toGMTString();
	}
	else var expires = "";
	document.cookie = name+"="+value+expires+"; path=/";
}

function readCookie(name) {
	var nameEQ = name + "=";
	var ca = document.cookie.split(';');
	for(var i=0;i < ca.length;i++) {
		var c = ca[i];
		while (c.charAt(0)==' ') c = c.substring(1,c.length);
		if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
	}
	return null;
}

function eraseCookie(name) {
	createCookie(name,"",-1);
}



function getParameterByName(name, url) {
  if (!url) url = window.location.href;
  name = name.replace(/[\[\]]/g, "\\$&");
  var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
    results = regex.exec(url);
  if (!results) return null;
  if (!results[2]) return '';
  return decodeURIComponent(results[2].replace(/\+/g, " "));
}

$.fn.isEmptyElement = function( ){
	return !$.trim($(this).html())
};

//workaround for jquery 3.x
if (typeof ($.fn.size)!="funcion")
  $.fn.size=function(){return this.length};