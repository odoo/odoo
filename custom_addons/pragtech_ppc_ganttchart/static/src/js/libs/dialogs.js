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

function centerPopup(url, target, w, h, scroll, resiz) {
	var winl = (screen.width - w) / 2;
	var wint = (screen.height - h) / 2;
	var winprops = 'height=' + h + ',width=' + w + ',top=' + wint + ',left=' + winl + ',scrollbars=' + scroll + ',resizable=' + resiz + ', toolbars=false, status=false, menubar=false';
	var win = window.open(url, target, winprops);
	if (!win)
		alert("A popup blocker was detected: please allow them for this application (check out the upper part of the browser window).");
	if (parseInt(navigator.appVersion) >= 4) {
		win.window.focus();
	}
}

function openCenteredWindow(url, target, winprops) {
	var prop_array = winprops.split(",");
	var i = 0;
	var w = 800;
	var h = 600;
	if (winprops && winprops != '') {
		while (i < prop_array.length) {
			if (prop_array[i].indexOf('width') > -1) {
				s = prop_array[i].substring(prop_array[i].indexOf('=') + 1);
				w = parseInt(s);
			} else if (prop_array[i].indexOf('height') > -1) {
				s = prop_array[i].substring(prop_array[i].indexOf('=') + 1);
				h = parseInt(s);
			}
			i += 1;
		}
		var winl = (screen.width - w) / 2;
		var wint = (screen.height - h) / 2;
		winprops = winprops + ",top=" + wint + ",left=" + winl;
	}
	win = window.open(url, target, winprops);
	if (!win)
		alert("A popup blocker was detected: please allow them for this application (check out the upper part of the browser window).");
	if (parseInt(navigator.appVersion) >= 4) {
		win.window.focus();
	}
}

function showFeedbackMessage(typeOrObject, message, title, autoCloseTime) {

	if(!autoCloseTime)
		autoCloseTime = 0;

	//console.debug("showFeedbackMessage",typeOrObject, message, title);
	var place = $("#__FEEDBACKMESSAGEPLACE");
	var mess;
	if (typeof(typeOrObject)=="object" )
		mess=typeOrObject;
	else
		mess = {type:typeOrObject, message:message,title:title};
	//if exists append error message
	var etm = $(".FFC_"+mess.type+":visible ._errorTemplateMessage");
	if(etm.length>0){
		etm.append("<hr>"+(mess.title?"<b>"+mess.title+"</b><br>":"")+mess.message+"<br>");
	}else{
		etm = $.JST.createFromTemplate(mess, "errorTemplate");
		place.append(etm);
		place.fadeIn();
	}

	if(autoCloseTime >0)
		setTimeout(function(){
			etm.fadeOut();
		},autoCloseTime);

		$(".FFC_OK").stopTime("ffchide").oneTime(1500, "ffchide",function () {$(this).fadeOut(400,function(){$(this)})});
		$(".FFC_WARNING").stopTime("ffchide").oneTime(75000, "ffchide",function () {$(this).fadeOut(400,function(){$(this)})});
		$(".FFC_ERROR").stopTime("ffchide").oneTime(10000, "ffchide",function () {$(this).fadeOut(400,function(){$(this)})});
}

function showFeedbackMessageInDiv(type, message, divId) {
	var place = $("#" + divId);
	var mess = {type:type, message:message};
	place.prepend($.JST.createFromTemplate(mess, "errorTemplate"));
	place.fadeIn();
	$("body").oneTime(1200, function () {
		$(".FFC_OK").fadeOut();
	});
}
function hideFeedbackMessages() {
  $("#__FEEDBACKMESSAGEPLACE").empty();
}


function submitInBlack(formId, actionHref, w, h) {

	if (!w)
		w = $(window).width() - 100;
	if (!h)
		h = $(window).height() - 50;

	openBlackPopup('', w + "px", h + "px", null, formId + "_ifr");
	var form = $("#" + formId);
	var oldAction = form.prop("action");
	var oldTarget = form.prop("target");
	form.prop("action", actionHref);
	form.prop("target", formId + "_ifr");
	$(window).data("openerForm", form);
	form.submit();
	form.prop("action", oldAction);
	if (oldTarget)
		form.prop("target", oldTarget);
	else
		form.removeAttr("target");
}


var __popups = [];
function createModalPopup(width, height, onCloseCallBack, cssClass, element, popupOpener) {
  //console.debug("createModalPopup");


  if (typeof(disableUploadize)=="function")
    disableUploadize();

  // se non diversamenete specificato l'openere è la window corrente;
  popupOpener = popupOpener || window;

	if (!width)
    width = "80%";

  if (!height)
    height = "80%";

  var localWidth=width,localHeight=height;

  if (typeof (width)=="string" && width.indexOf("%")>0 ) {
    localWidth = function () {return ($(window).width() * parseFloat(width)) / 100};
  }

	if (typeof (height)=="string" && height.indexOf("%")>0)
    localHeight = function(){return ($(window).height() *  parseFloat(height)) / 100};

	var popupWidth = localWidth, popupHeight = localHeight;

	if(typeof localWidth == "function")
		popupWidth = localWidth();

	if(typeof localHeight == "function")
		popupHeight = localHeight();

	popupWidth = parseFloat(popupWidth);
	popupHeight = parseFloat(popupHeight);

	if (typeof onCloseCallBack == "string")
		cssClass = onCloseCallBack;

	//$("#__popup__").remove();

	var popupN = __popups.length+1;
	__popups.push("__popup__" + popupN);

	var isInIframe = isIframe();

	var bg = $("<div>").prop("id", "__popup__" + popupN);
	bg.addClass("modalPopup" + (isInIframe ? " inIframe" : "")).hide();

	if (cssClass)
		bg.addClass(cssClass);

	function getMarginTop(){
		var mt = ($(window).height() - popupHeight)/2 - 100;
		return mt < 0 ? 10 : mt;
	}

	var internalDiv=$("<div>").addClass("bwinPopupd").css({ width:popupWidth, minHeight:popupHeight, marginTop: getMarginTop(), maxHeight:$(window).height()-20, overflow: "auto" });

	$(window).off("resize.popup"+popupN).on("resize.popup"+popupN, function(){

		if(typeof localWidth == "function")
			popupWidth = localWidth();

		if(typeof localHeight == "function")
			popupHeight = localHeight();

		internalDiv.css({ width:popupWidth, minHeight:popupHeight });

		var w = internalDiv.outerWidth() > $(window).width()-20 ? $(window).width()-20 : popupWidth;
		var h = internalDiv.outerHeight() > $(window).height()-20 ? $(window).height()-20 : popupHeight;

    internalDiv.css({ marginTop: getMarginTop(), minHeight: h, maxHeight:$(window).height()-20,minWidth: w });

	});

	bg.append(internalDiv);

	var showBG = function(el, time, callback){

		if (isInIframe) {
			internalDiv.css({marginTop: -50 });
			el.show();
			internalDiv.animate({marginTop: 0}, (time/2), callback);
		} else {
			internalDiv.css({opacity: 0, top: -50}).show();
			el.fadeIn(time, function () {
				internalDiv.animate({top: 0, opacity: 1}, time/3, callback);
			});
		}

/*
		if(isInIframe) {
			internalDiv.css({marginTop: -1000 });
			el.show();
			internalDiv.animate({marginTop: 0}, (time * 2), callback);
		}else{
			internalDiv.css({opacity:0, top: -500}).show();
			el.fadeIn(time, function(){
				internalDiv.animate({top: 0, opacity:1}, time, callback);
			});
		}
*/

		return this;
	};

	if(!element)
		$("#twMainContainer").addClass("blur");

	showBG(bg, 300, function(){})
	bg.on("click",function(event){
		if ($(event.target).closest(".bwinPopupd").length <= 0)
			bg.trigger("close");
	});

	var close = $("<span class=\"teamworkIcon close popUpClose\" style='cursor:pointer;position:absolute;'>x</span>");
	internalDiv.append(close);

	close.click(function () {
		bg.trigger("close");
	});

	$("body").css({overflowY:"hidden"});

	if(!element){
		$("body").append(bg);
	}else{
		element.after(bg);
	}

	//close call callback
	bg.on("close", function () {
		var callBackdata = $(this).data("callBackdata");
    var ndo=bg;

    if (typeof (enableUploadize)=="function")
		  enableUploadize();

    //console.debug("ndo",ndo);

		var alertMsg;
    var ifr=bg.find("iframe");

    if (ifr.length>0){
      try {
        alertMsg = ifr.get(0).contentWindow.alertOnUnload();
      }catch (e){}
    } else {
      alertMsg=alertOnUnload(ndo);
    }

    if (alertMsg){
      if (!confirm(alertMsg))
        return;
    }

    bg.fadeOut(100, function () {

      $(window).off("resize.popup"+popupN);
      bg.remove();
      __popups.pop();

      if (__popups.length == 0)
        $("#twMainContainer").removeClass("blur");

      if (typeof(onCloseCallBack) == "function")
        onCloseCallBack(callBackdata);

      $("body").css({overflowY: "auto"});
    });

	});

	//destroy do not call callback
	bg.on("destroy", function () {
		bg.remove();
		$("body").css({overflowY: "auto"});
	});

  //rise resize event in order to show buttons
  $("body").oneTime(1000,"br",function(){$(this).resize();}); // con meno di 1000 non funziona


  //si deposita l'popupOpener sul bg. Per riprenderlo si usa getBlackPopupOpener()
  bg.data("__opener",popupOpener);

  return internalDiv;
}

function changeModalSize(w,h){
	var newDim = {};
	if(w)
		newDim.width = w;
	if(h)
		newDim.minHeight = h;

	var isInIframe = isIframe();
	var popUp = isInIframe ? window.parent.$(".bwinPopupd") : $(".bwinPopupd");

	if(popUp.length)
		popUp.delay(300).animate(newDim, 200);
}

function openBlackPopup(url, width, height, onCloseCallBack, iframeId, cssClass) {

	if (!iframeId)
		iframeId = "bwinPopupIframe";

	//add black only if not already in blackpupup
	var color= cssClass ? cssClass + " iframe" : "iframe";

	var ndo = top.createModalPopup(width, height, onCloseCallBack, color,null,window);

  //ndo.closest(".modalPopup ").data("__opener",window);  // si deposita il vero opener

  var isInIframe = isIframe();

	ndo.append("<div class='bwinPopupIframe_wrapper'><iframe id='" + iframeId + "' name='" + iframeId + "' frameborder='0'></iframe></div>");
	ndo.find("iframe:first").prop("src", url).css({width:"100%", height:"100%", backgroundColor: isInIframe ? '#F9F9F9' : '#FFFFFF'});
}

function getBlackPopup() {
	var ret=$([]);
	if (__popups.length>0) {
		var id = __popups[__popups.length - 1];
		ret = $("#" + id);
	}
	if (ret.length==0 && window!=top) {
		ret = window.parent.getBlackPopup();
	}
	return ret;
}


function getBlackPopupOpener(){
  return getBlackPopup().data("__opener")
}

function closeBlackPopup(callBackdata) {
	//console.debug("closeBlackPopup ",callBackdata);
	var bp = getBlackPopup();

	if (callBackdata)
		bp.data("callBackdata",callBackdata);
	bp.trigger("close");
}

function openPopUp(el,width,height){
	var popup=createModalPopup(width,height);
	popup.append(el.clone().show());
}

//returns a jquery object where to write content

function isIframe() {
	var isIframe = false;
	try{
		//try to access the document object
		if (self.location.href != top.location.href)
			isIframe = true;
	}catch(e) {
		//We don't have access, it's cross-origin!
		isIframe = true;
	}
	return isIframe;
};


function openBulkAction(bulkDivId){
	var popup=createModalPopup(500,300);
	popup.append($("#"+bulkDivId).clone().show());
}


function refreshBulk(el) {
	//console.debug("refreshBulk")

	if (el.is(":checked"))
		el.closest("tr").addClass("selected");
	else
		el.closest("tr").removeClass("selected");

	var table=el.closest(".dataTable");
	if (table.find(".selected :checked").length > 0) {

		$("#bulkOp #bulkRowSel").html(table.find("tbody > tr.selected").length + "/" + table.children("tbody").children("tr").length);

		var bukOpt = $("#bulkOp").clone().addClass("bulkOpClone");
		bukOpt.fadeIn(200, function(){
			$("#bulkPlace").html(bukOpt);
			$.tableHF.refreshTfoot();
		});

	} else {
		$(".bulkOpClone").fadeOut(200, function(){
			$.tableHF.refreshTfoot();
		});
	}
}

function selUnselAll(el){
	//var bulkCheckbox = $("#multi td [type='checkbox']");
	var bulkCheckbox = el.closest(".dataTable").find("[type='checkbox']");
	if (el.is(":checked")){
		bulkCheckbox.prop("checked", true);
		bulkCheckbox.closest("tr").addClass("selected");
	} else {
		bulkCheckbox.prop("checked", false);
		bulkCheckbox.closest("tr").removeClass("selected");
	}

	refreshBulk(el);
}
