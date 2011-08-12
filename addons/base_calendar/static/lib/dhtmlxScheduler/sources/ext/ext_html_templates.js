/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTemplatesReady",function(){
	var els = document.body.getElementsByTagName("DIV");
	for (var i=0; i < els.length; i++) {
		var cs = els[i].className||"";
		cs = cs.split(":");
		if (cs.length == 2 && cs[0] == "template"){
			var code = "return \""+(els[i].innerHTML||"").replace(/\"/g,"\\\"").replace(/[\n\r]+/g,"")+"\";";
			code = unescape(code).replace(/\{event\.([a-z]+)\}/g,function(all,mask){
				return '"+ev.'+mask+'+"';
			});
			scheduler.templates[cs[1]]=Function("start","end","ev",code);
			els[i].style.display='none';
		}
	};
})