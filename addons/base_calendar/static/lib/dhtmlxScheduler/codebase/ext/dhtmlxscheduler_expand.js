/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
scheduler.expand=function(){var A=scheduler._obj;do{A._position=A.style.position||"";A.style.position="static"}while((A=A.parentNode)&&A.style);A=scheduler._obj;A.style.position="absolute";A._width=A.style.width;A._height=A.style.height;A.style.width=A.style.height="100%";A.style.top=A.style.left="0px";var B=document.body;B.scrollTop=0;B=B.parentNode;if(B){B.scrollTop=0}document.body._overflow=document.body.style.overflow||"";document.body.style.overflow="hidden";scheduler._maximize()};scheduler.collapse=function(){var A=scheduler._obj;do{A.style.position=A._position}while((A=A.parentNode)&&A.style);A=scheduler._obj;A.style.width=A._width;A.style.height=A._height;document.body.style.overflow=document.body._overflow;scheduler._maximize()};scheduler.attachEvent("onTemplatesReady",function(){var A=document.createElement("DIV");A.className="dhx_expand_icon";scheduler.toggleIcon=A;scheduler._obj.appendChild(A);A.onclick=function(){if(!scheduler.expanded){scheduler.expand()}else{scheduler.collapse()}}});scheduler._maximize=function(){this.expanded=!this.expanded;this.toggleIcon.style.backgroundPosition="0px "+(this._expand?"0":"18")+"px";if(scheduler.callEvent("onSchedulerResize",[])){scheduler.update_view()}};