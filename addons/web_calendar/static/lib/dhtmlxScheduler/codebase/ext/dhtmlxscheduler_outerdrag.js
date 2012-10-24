/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in non-GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTemplatesReady",function(){var a=new dhtmlDragAndDropObject,e=a.stopDrag,b;a.stopDrag=function(c){b=c||event;return e.apply(this,arguments)};a.addDragLanding(scheduler._els.dhx_cal_data[0],{_drag:function(c,a,e,h){if(!scheduler.checkEvent("onBeforeExternalDragIn")||scheduler.callEvent("onBeforeExternalDragIn",[c,a,e,h,b])){var i=scheduler.attachEvent("onEventCreated",function(a,b){if(!scheduler.callEvent("onExternalDragIn",[a,c,b]))this._drag_mode=this._drag_id=null,this.deleteEvent(a)});
if(scheduler.matrix&&scheduler.matrix[scheduler._mode])scheduler.dblclick_dhx_matrix_cell(b);else{var g=document.createElement("div");g.className="dhx_month_body";var d={},f;for(f in b)d[f]=b[f];d.target=d.srcElement=g;scheduler._on_dbl_click(d)}scheduler.detachEvent(i)}},_dragIn:function(a){return a},_dragOut:function(){return this}})});
