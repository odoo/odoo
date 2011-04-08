//lame old code doesn't provide raw event object
		scheduler.attachEvent("onTemplatesReady", function(){
		
			var dragger = (new dhtmlDragAndDropObject());
			var old = dragger.stopDrag;
			var last_event;
			dragger.stopDrag = function(e){
				last_event = e||event;
				return old.apply(this, arguments);
			};
			dragger.addDragLanding(scheduler._els["dhx_cal_data"][0],{
				_drag:function(sourceHtmlObject,dhtmlObject,targetHtmlObject){
					
					var temp = scheduler.attachEvent("onEventCreated", function(id,e){
						if (!scheduler.callEvent("onExternalDragIn", [id, sourceHtmlObject, e])){
							this._drag_mode = this._drag_id = null;
							this.deleteEvent(id);
						}
					});
					
					if (scheduler.matrix[scheduler._mode])	
						scheduler.dblclick_dhx_matrix_cell(last_event);
					else
						scheduler._on_dbl_click(last_event);
						
					scheduler.detachEvent(temp);
					
					
				},
				_dragIn:function(htmlObject,shtmlObject){
					return htmlObject;
				},
				_dragOut:function(htmlObject){
					return this;
				}
			});
		
		});