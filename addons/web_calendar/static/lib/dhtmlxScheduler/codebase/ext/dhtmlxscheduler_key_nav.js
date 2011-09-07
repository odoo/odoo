/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){var b=!1;scheduler.attachEvent("onBeforeLightbox",function(){return b=!0});scheduler.attachEvent("onAfterLightbox",function(){b=!1;return!0});dhtmlxEvent(document,_isOpera?"keypress":"keydown",function(a){a=a||event;if(!b)if(a.keyCode==37||a.keyCode==39){a.cancelBubble=!0;var e=scheduler.date.add(scheduler._date,a.keyCode==37?-1:1,scheduler._mode);scheduler.setCurrentView(e);return!0}else if(a.ctrlKey&&a.keyCode==67)scheduler._copy_id=scheduler._select_id;else if(a.ctrlKey&&a.keyCode==
86){var c=scheduler.getEvent(scheduler._copy_id);if(c){var d=scheduler._copy_event(c);d.id=scheduler.uid();scheduler.addEvent(d)}}})})();
