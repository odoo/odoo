/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTemplatesReady",function(){var a=new dhtmlDragAndDropObject,g=a.stopDrag,b;a.stopDrag=function(d){b=d||event;return g.apply(this,arguments)};a.addDragLanding(scheduler._els.dhx_cal_data[0],{_drag:function(d){var a=scheduler.attachEvent("onEventCreated",function(a,b){if(!scheduler.callEvent("onExternalDragIn",[a,d,b]))this._drag_mode=this._drag_id=null,this.deleteEvent(a)});if(scheduler.matrix&&scheduler.matrix[scheduler._mode])scheduler.dblclick_dhx_matrix_cell(b);else{var f=
document.createElement("div");f.className="dhx_month_body";var c={},e;for(e in b)c[e]=b[e];c.target=c.srcElement=f;scheduler._on_dbl_click(c)}scheduler.detachEvent(a)},_dragIn:function(a){return a},_dragOut:function(){return this}})});
