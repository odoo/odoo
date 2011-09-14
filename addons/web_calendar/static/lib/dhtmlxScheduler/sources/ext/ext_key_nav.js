/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
//Initial idea and implementation by Steve MC
(function (){

var lightboxopen = false;

scheduler.attachEvent("onBeforeLightbox",function(){ lightboxopen = true; return true; });
scheduler.attachEvent("onAfterLightbox",function(){ lightboxopen = false; return true; });

dhtmlxEvent(document,(_isOpera?"keypress":"keydown"),function(e){
	e=e||event;
	if (!lightboxopen){
		
		if (e.keyCode == 37 || e.keyCode == 39) { // Left-Arrow
			e.cancelBubble = true;
			
		    var next = scheduler.date.add(scheduler._date,(e.keyCode == 37 ? -1 : 1 ),scheduler._mode);
		    scheduler.setCurrentView(next);
		    return true;
		} else if (e.ctrlKey && e.keyCode == 67){
			scheduler._copy_id = scheduler._select_id;
		} else if (e.ctrlKey && e.keyCode == 86){
			var ev = scheduler.getEvent(scheduler._copy_id);
			if (ev){
				var new_ev = scheduler._copy_event(ev);
					new_ev.id = scheduler.uid();
					scheduler.addEvent(new_ev);
			}
		}
	}
});

})();