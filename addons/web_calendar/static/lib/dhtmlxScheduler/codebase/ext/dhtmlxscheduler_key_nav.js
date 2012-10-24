/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){var g=!1,h,d=null;scheduler.attachEvent("onBeforeLightbox",function(){return g=!0});scheduler.attachEvent("onAfterLightbox",function(){g=!1;return!0});scheduler.attachEvent("onMouseMove",function(b,a){h=scheduler.getActionData(a).date});dhtmlxEvent(document,_isOpera?"keypress":"keydown",function(b){b=b||event;if(!g){var a=window.scheduler;if(b.keyCode==37||b.keyCode==39){b.cancelBubble=!0;var j=a.date.add(a._date,b.keyCode==37?-1:1,a._mode);a.setCurrentView(j);return!0}var e=a._select_id;
if(b.ctrlKey&&b.keyCode==67){if(e)a._buffer_id=e,d=!0,a.callEvent("onEventCopied",[a.getEvent(e)]);return!0}if(b.ctrlKey&&b.keyCode==88&&e){d=!1;a._buffer_id=e;var c=a.getEvent(e);a.updateEvent(c.id);a.callEvent("onEventCut",[c])}if(b.ctrlKey&&b.keyCode==86){if(c=a.getEvent(a._buffer_id)){var i=c.end_date-c.start_date;if(d){var f=a._lame_clone(c);f.id=a.uid();f.start_date=new Date(h);f.end_date=new Date(f.start_date.valueOf()+i);a.addEvent(f);a.callEvent("onEventPasted",[d,f,c])}else{var k=a._lame_copy({},
c);c.start_date=new Date(h);c.end_date=new Date(c.start_date.valueOf()+i);a.render_view_data();a.callEvent("onEventPasted",[d,c,k]);d=!0}}return!0}}})})();
