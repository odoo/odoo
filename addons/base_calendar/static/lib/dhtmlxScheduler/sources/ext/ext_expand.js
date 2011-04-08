scheduler.expand = function(){
      var t = scheduler._obj;
      do {
         t._position = t.style.position||"";
         t.style.position = "static";
      } while ((t = t.parentNode) && t.style );
	  t = scheduler._obj;
      t.style.position="absolute";
      t._width = t.style.width;
      t._height = t.style.height;
      t.style.width = t.style.height = "100%";
      t.style.top = t.style.left = "0px";
      
	  var top =document.body;
	  	  top.scrollTop = 0;
	  	  
	  top = top.parentNode;
	  if (top)
   		  top.scrollTop = 0;
   	  document.body._overflow=document.body.style.overflow||"";
   	  document.body.style.overflow = "hidden";
	  scheduler._maximize()
}
   
scheduler.collapse = function(){
      var t = scheduler._obj;
      do {
         t.style.position = t._position;
      } while ((t = t.parentNode) && t.style );
	  t = scheduler._obj;
      t.style.width = t._width;
      t.style.height = t._height;
      document.body.style.overflow=document.body._overflow;
	  scheduler._maximize()
}
   
scheduler.attachEvent("onTemplatesReady",function(){
   var t = document.createElement("DIV");
   t.className="dhx_expand_icon";
   scheduler.toggleIcon = t;
   scheduler._obj.appendChild(t);   
   t.onclick = function(){
      if (!scheduler.expanded)
         scheduler.expand();
      else 
         scheduler.collapse();
   }
});
scheduler._maximize = function(){
	  this.expanded = !this.expanded;
      this.toggleIcon.style.backgroundPosition="0px "+(this._expand?"0":"18")+"px";
      if (scheduler.callEvent("onSchedulerResize",[]))
         scheduler.update_view();
}
