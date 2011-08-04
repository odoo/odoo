/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler._extra_xle = false; // flag if we are calling xle once again (we don't want to get into loop with scheduler.parse)
scheduler.attachEvent("onXLE", function(){
    if(!scheduler._extra_xle){
        var isEventsLoaded = false;
        for(var key in scheduler._events){
            if(scheduler._events[key].text) {
                isEventsLoaded = true;
                break;
            }
        }
        if((localStorage._updated_events || !isEventsLoaded) && localStorage._events) {
            scheduler._extra_xle = true;
            scheduler.parse(localStorage._events, "json");
            scheduler._extra_xle = false;
            var dp = scheduler._dataprocessor;
            var updatedEvents = JSON.parse(localStorage._updated_events);
            dp.setUpdateMode("off");
            for(var id in updatedEvents)
                dp.setUpdated(id,true,updatedEvents[id]);
            dp.sendData();
            dp.setUpdateMode("cell");
        }
    }
});
scheduler.attachEvent("onBeforeEventDelete", function(id, object){
    var status = scheduler._dataprocessor.getState(id);
    if(status == 'inserted' && localStorage._updated_events) {
        var updated_events = JSON.parse(localStorage._updated_events);
        delete updated_events[id];
        for(var id in updated_events){
            localStorage._updated_events = JSON.stringify(updated_events);
            break;
        }      
    }
    return true;
});

var old_delete_event = scheduler.deleteEvent;
scheduler.deleteEvent = function(id, silent){
    old_delete_event.apply(this, arguments);
    localStorage._events = scheduler.toJSON();
};

scheduler._offline = {};
scheduler._offline._after_update_events = [];

var old_dp_init = scheduler._dp_init;
scheduler._dp_init = function(dp){
    old_dp_init.apply(this, arguments);
    
    dp.attachEvent("onAfterUpdate",function(sid,action,tid,xml_node){
        scheduler._offline._after_update_events.push(sid);
        return true;
    });
    dp.attachEvent("onAfterUpdateFinish",function(sid,action,tid,xml_node){
        localStorage._events = scheduler.toJSON();
        var updated_events = JSON.parse(localStorage._updated_events);
        for(var i=0; i<scheduler._offline._after_update_events.length; i++){
            delete updated_events[scheduler._offline._after_update_events[i]];
        }
        var eventsLeft = false;
        for(var id in updated_events){
            eventsLeft = true;
            break;
        }
        if(eventsLeft) {
            localStorage._updated_events = JSON.stringify(updated_events);
            scheduler._offline._after_update_event = [];
        }
        else {
            delete localStorage._updated_events;
        }
        return true;
    });
    dp.attachEvent("onBeforeDataSending",function(id, b, rows){
        var updated_events = {};
        if(localStorage._updated_events)
            updated_events = JSON.parse(localStorage._updated_events);

        for(var ev_id in rows){
            var param = scheduler._dataprocessor.action_param;
            if((updated_events[ev_id] && (updated_events[ev_id][param] == 'inserted' || rows[ev_id][param] == 'deleted')) || !updated_events[ev_id])
                updated_events[ev_id] = rows[ev_id][param];
        }

        localStorage._events = scheduler.toJSON();
        localStorage._updated_events = JSON.stringify(updated_events);

        return true;
    });
    dhtmlxError.catchError("LoadXML",function(a,b,xml){
        for(var key in scheduler._dataprocessor._in_progress) {
            delete scheduler._dataprocessor._in_progress[key];
        }
    });

};

