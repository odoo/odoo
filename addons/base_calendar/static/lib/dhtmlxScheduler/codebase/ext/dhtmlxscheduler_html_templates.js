/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTemplatesReady",function(){for(var c=document.body.getElementsByTagName("DIV"),b=0;b<c.length;b++){var a=c[b].className||"",a=a.split(":");if(a.length==2&&a[0]=="template"){var d='return "'+(c[b].innerHTML||"").replace(/\"/g,'\\"').replace(/[\n\r]+/g,"")+'";',d=unescape(d).replace(/\{event\.([a-z]+)\}/g,function(b,a){return'"+ev.'+a+'+"'});scheduler.templates[a[1]]=Function("start","end","ev",d);c[b].style.display="none"}}});
