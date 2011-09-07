/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onLightBox",function(){
	if (this._cover){
		try{
			this._cover.style.height = this.expanded ? "100%" : ((document.body.parentNode||document.body).scrollHeight+"px");
		} catch(e) {};
	}
});

scheduler.form_blocks.select.set_value=function(node,value,ev){
	if (typeof value == "undefined" || value === "")
		value = (node.firstChild.options[0]||{}).value;
	node.firstChild.value=value||"";
};