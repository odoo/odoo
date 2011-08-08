/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTimelineCreated", function (obj){

	if(obj.render == "tree") {
		obj.y_unit_original = obj.y_unit;
		obj.y_unit = scheduler._getArrayToDisplay(obj.y_unit_original);

        scheduler.attachEvent('onOptionsLoadStart', function(){
            obj.y_unit = scheduler._getArrayToDisplay(obj.y_unit_original);
        });
		
		scheduler.form_blocks[obj.name]={
			render:function(sns) {
				var _result = "<div class='dhx_section_timeline' style='overflow: hidden; height: "+sns.height+"px'></div>";
				return _result;
			},
			set_value:function(node,value,ev,config){
				var options = scheduler._getArrayForSelect(scheduler.matrix[config.type].y_unit_original, config.type);
				node.innerHTML = '';
				var temp_select = document.createElement('select');
				node.appendChild(temp_select);
				
				var select = node.getElementsByTagName('select')[0];
				
				for(var i=0; i<options.length; i++) {
					var temp_option = document.createElement('option');
					temp_option.value = options[i].key;
					if(temp_option.value == ev[scheduler.matrix[config.type].y_property])
						temp_option.selected = true;
					temp_option.innerHTML = options[i].label;
					select.appendChild(temp_option);
				}
				
			},
			get_value:function(node,ev,config){
				return  node.firstChild.value;
			},
			focus:function(node){
			}
		};
	}
});	

scheduler.attachEvent("onBeforeViewRender", function (render_name, y_unit, timeline){
	var res = {};
	if(render_name == "tree"){
		var height;
		// section 1
		var tr_className, style_height, td_className;
		var div_expand;
		// section 3
		var table_className;
		if(y_unit.children) {
			height = timeline.folder_dy||timeline.dy;
			if(timeline.folder_dy && !timeline.section_autoheight) {
				style_height = "height:"+timeline.folder_dy+"px;";
			}
			tr_className = "dhx_row_folder";
			td_className = "dhx_matrix_scell folder";
			div_expand = "<div class='dhx_scell_expand'>"+((y_unit.open)?'-':'+')+"</div>";
			table_className = (timeline.folder_events_available)?"dhx_data_table folder_events":"dhx_data_table folder";
		} else {
			height = timeline.dy;
			tr_className = "dhx_row_item";
			td_className = "dhx_matrix_scell item";
			div_expand = '';
			table_className = "dhx_data_table";
		}
		td_content = "<div class='dhx_scell_level"+y_unit.level+"'>"+div_expand+"<div class='dhx_scell_name'>"+(scheduler.templates[timeline.name+'_scale_label'](y_unit.key, y_unit.label, y_unit)||y_unit.label)+"</div></div>";
		
		res = {
			height: height,
			style_height: style_height,
			//section 1
			tr_className: tr_className,
			td_className: td_className,
			td_content: td_content,
			//section 3
			table_className: table_className
		};
	};
	return res;
});

var section_id_before; // section id of the event before dragging (to bring it back if user drop's event on folder without folder_events_available)

scheduler.attachEvent("onBeforeEventChanged", function(event_object, native_event, is_new) {
	if (scheduler._isRender("tree")) { // if mode's render == tree
		var section = scheduler.getSection(event_object[scheduler.matrix[scheduler._mode].y_property]);
		if (typeof section.children != 'undefined' && !scheduler.matrix[scheduler._mode].folder_events_available) {
			if (!is_new) { //if old - move back
				event_object[scheduler.matrix[scheduler._mode].y_property] = section_id_before;
			}
			return false;
		}
	}
	return true;
});

scheduler.attachEvent("onBeforeDrag", function (event_id, mode, native_event_object){
	var cell = scheduler._locate_cell_timeline(native_event_object);
	if(cell) {
		var section_id = scheduler.matrix[scheduler._mode].y_unit[cell.y].key;
		if(typeof scheduler.matrix[scheduler._mode].y_unit[cell.y].children != "undefined" && !scheduler.matrix[scheduler._mode].folder_events_available) {
			return false;
		}
	}	
	if(scheduler._isRender("tree")) {
		ev = scheduler.getEvent(event_id);
		section_id_before = section_id||ev[scheduler.matrix[scheduler._mode].y_property]; // either event id or section_id will be available
	}
	return true;
});		

scheduler._getArrayToDisplay = function(array){ // function to flatten out hierarhical array, used for tree view
	var result = [];
	var fillResultArray = function(array, lvl){
		var level = lvl||0;
		for(var i=0; i<array.length; i++) {
			array[i].level = level;
			if(typeof array[i].children != "undefined" && typeof array[i].key == "undefined")
				array[i].key=scheduler.uid();
			result.push(array[i]);
			if(array[i].open && array[i].children) {
				fillResultArray(array[i].children, level+1);
			} 
		}
	};
	fillResultArray(array);
	return result;
};


scheduler._getArrayForSelect = function(array, mode){ // function to flatten out hierarhical array, used for tree view
	var result = [];
	var fillResultArray = function(array){
		for(var i=0; i<array.length; i++) {
			if(scheduler.matrix[mode].folder_events_available) {
				result.push(array[i]);
			}
			else {
				if(typeof array[i].children == "undefined") {
					result.push(array[i]);
				}
			}
			if(array[i].children) 
				fillResultArray(array[i].children, mode);
		}
	};
	fillResultArray(array);
	return result;
};


/*
scheduler._toggleFolderDisplay(4) -- toggle display of the section with key 4 (closed -> open)
scheduler._toggleFolderDisplay(4, true) -- open section with the key 4 (doesn't matter what status was before). False - close.
scheduler._toggleFolderDisplay(4, false, true) -- close ALL sections. Key is not used in such condition.
*/
scheduler._toggleFolderDisplay = function(key, status, all_sections){ // used for tree view
	var marked;
	var toggleElement = function(key, array, status, all_sections) {
		for (var i=0; i<array.length; i++) {
			if((array[i].key == key || all_sections) && array[i].children) {
				array[i].open = (typeof status != "undefined") ? status : !array[i].open;
				marked = true;
				if(!all_sections && marked) 
					break;
			}
			if(array[i].children) {
				toggleElement(key,array[i].children, status, all_sections);
			}
		}
	};
	toggleElement(key,scheduler.matrix[scheduler._mode].y_unit_original, status, all_sections);
	scheduler.matrix[scheduler._mode].y_unit = scheduler._getArrayToDisplay(scheduler.matrix[scheduler._mode].y_unit_original);
	scheduler.callEvent("onOptionsLoad",[]);
};

scheduler.attachEvent("onCellClick", function (x, y, a, b, event){
	if(scheduler._isRender("tree")) {
		if(!scheduler.matrix[scheduler._mode].folder_events_available) {
			if(typeof scheduler.matrix[scheduler._mode].y_unit[y].children != "undefined") {
				scheduler._toggleFolderDisplay(scheduler.matrix[scheduler._mode].y_unit[y].key);
			}
		}
	}
});

scheduler.attachEvent("onYScaleClick", function (index, value, event){
	if(scheduler._isRender("tree")) {
		if(typeof value.children != "undefined") {
			scheduler._toggleFolderDisplay(value.key);
		}
	}
});

scheduler.getSection = function(id){
	if(scheduler._isRender("tree")) {
		var obj;
		var findElement = function(key, array) {
			for (var i=0; i<array.length; i++) {
				if(array[i].key == key) 
					obj = array[i];
				if(array[i].children) 
					findElement(key,array[i].children);
			}
		};
		findElement(id, scheduler.matrix[scheduler._mode].y_unit_original);
		return obj||null;
	}
};

scheduler.deleteSection = function(id){
	if(scheduler._isRender("tree")) {
		var result = false;
		var deleteElement = function(key, array) {
			for (var i=0; i<array.length; i++) {
				if(array[i].key == key) {
					array.splice(i,1);
					result = true;
				}
				if(result) 
					break;
				if(array[i].children) 
					deleteElement(key,array[i].children);
			}
		};
		deleteElement(id, scheduler.matrix[scheduler._mode].y_unit_original);	
		scheduler.matrix[scheduler._mode].y_unit = scheduler._getArrayToDisplay(scheduler.matrix[scheduler._mode].y_unit_original);
		scheduler.callEvent("onOptionsLoad",[]);	
		return result;
	}	
};

scheduler.deleteAllSections = function(){
    if(scheduler._isRender("tree")) {
        scheduler.matrix[scheduler._mode].y_unit_original = [];
        scheduler.matrix[scheduler._mode].y_unit = scheduler._getArrayToDisplay(scheduler.matrix[scheduler._mode].y_unit_original);
        scheduler.callEvent("onOptionsLoad",[]);
    }
};

scheduler.addSection = function(obj, parent_id){
	if(scheduler._isRender("tree")) {
		var result = false;
		var addElement = function(obj, parent_key, array) {
			if(!parent_id) {
				array.push(obj);
				result = true;
			}
			else {
				for (var i=0; i<array.length; i++) {
					if(array[i].key == parent_key && typeof array[i].children != "undefined") {
						array[i].children.push(obj);
						result = true;
					}
					if(result) 
						break;
					if(array[i].children) 
						addElement(obj,parent_key,array[i].children);
				}
			}
		};
		addElement(obj, parent_id, scheduler.matrix[scheduler._mode].y_unit_original);	
		scheduler.matrix[scheduler._mode].y_unit = scheduler._getArrayToDisplay(scheduler.matrix[scheduler._mode].y_unit_original);
		scheduler.callEvent("onOptionsLoad",[]);	
		return result;
	}	
};


scheduler.openAllSections = function() {
	if(scheduler._isRender("tree")) 
		scheduler._toggleFolderDisplay(1, true, true);
};
scheduler.closeAllSections = function() {
	if(scheduler._isRender("tree")) 
		scheduler._toggleFolderDisplay(1, false, true);
};
scheduler.openSection = function(section_id){
	if(scheduler._isRender("tree")) 
		scheduler._toggleFolderDisplay(section_id, true);
};
scheduler.closeSection = function(section_id){
	if(scheduler._isRender("tree")) 
		scheduler._toggleFolderDisplay(section_id, false);
};
