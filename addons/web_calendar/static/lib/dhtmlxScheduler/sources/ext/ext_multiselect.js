/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.form_blocks["multiselect"]={
	render:function(sns) {
		var _result = "<div class='dhx_multi_select_"+sns.name+"' style='overflow: auto; height: "+sns.height+"px; position: relative;' >";
		for (var i=0; i<sns.options.length; i++) {
			_result += "<label><input type='checkbox' value='"+sns.options[i].key+"'/>"+sns.options[i].label+"</label>";
			if(convertStringToBoolean(sns.vertical)) _result += '<br/>';
		}
		_result += "</div>";
		return _result;
	},
	set_value:function(node,value,ev,config){
		
		var _children = node.getElementsByTagName('input');
		for(var i=0;i<_children.length;i++) {
			_children[i].checked = false; //unchecking all inputs on the form
		}
		
		function _mark_inputs(ids) { // ids = [ 0: undefined, 1: undefined, 2: true ... ]
			var _children = node.getElementsByTagName('input');
			for(var i=0;i<_children.length; i++) {
				_children[i].checked = !! ids[_children[i].value];
			}			
		}
		
		if(!scheduler._new_event) { // if it is a new event - new to get saved options
			var _ids = [];
			if(ev[config.map_to]) {
				var results = ev[config.map_to].split(',');
				for(var i=0;i<results.length;i++){
					_ids[results[i]] = true;
				}
				_mark_inputs(_ids);
			}
			else {
				var divLoading = document.createElement('div');
				divLoading.className='dhx_loading';
				divLoading.style.cssText = "position: absolute; top: 40%; left: 40%;";
				node.appendChild(divLoading);
				dhtmlxAjax.get(config.script_url+'?dhx_crosslink_'+config.map_to+'='+ev.id+'&uid='+scheduler.uid(), function(loader) {
					var _result = loader.doXPath("//data/item");
					var _ids = [];
					for(var i=0;i<_result.length;i++){ 
						_ids[_result[i].getAttribute(config.map_to)] = true;
					}
					_mark_inputs(_ids);
					node.removeChild(divLoading);
				});
			}
		}
	},
	get_value:function(node,ev,config){
		var _result = [];
		var _children = node.getElementsByTagName("input");
		for(var i=0;i<_children.length;i++) {
			if(_children[i].checked)
				_result.push(_children[i].value); 
		}
		return _result.join(','); 
	},
	
	focus:function(node){
	}
};