/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
scheduler.attachEvent("onTemplatesReady",function(){var C=(new dhtmlDragAndDropObject());var B=C.stopDrag;var A;C.stopDrag=function(D){A=D||event;return B.apply(this,arguments)};C.addDragLanding(scheduler._els.dhx_cal_data[0],{_drag:function(F,G,D){var E=scheduler.attachEvent("onEventCreated",function(I,H){if(!scheduler.callEvent("onExternalDragIn",[I,F,H])){this._drag_mode=this._drag_id=null;this.deleteEvent(I)}});if(scheduler.matrix[scheduler._mode]){scheduler.dblclick_dhx_matrix_cell(A)}else{scheduler._on_dbl_click(A)}scheduler.detachEvent(E)},_dragIn:function(E,D){return E},_dragOut:function(D){return this}})});