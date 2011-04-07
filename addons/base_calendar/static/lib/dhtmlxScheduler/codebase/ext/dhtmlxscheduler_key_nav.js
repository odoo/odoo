/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
(function(){var A=false;scheduler.attachEvent("onBeforeLightbox",function(){A=true;return true});scheduler.attachEvent("onAfterLightbox",function(){A=false;return true});dhtmlxEvent(document,(_isOpera?"keypress":"keydown"),function(D){D=D||event;if(!A){if(D.keyCode==37||D.keyCode==39){D.cancelBubble=true;var B=scheduler.date.add(scheduler._date,(D.keyCode==37?-1:1),scheduler._mode);scheduler.setCurrentView(B);return true}else{if(D.ctrlKey&&D.keyCode==67){scheduler._copy_id=scheduler._select_id}else{if(D.ctrlKey&&D.keyCode==86){var C=scheduler.getEvent(scheduler._copy_id);if(C){var E=scheduler._copy_event(C);E.id=scheduler.uid();scheduler.addEvent(E)}}}}}})})();