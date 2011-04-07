scheduler.attachEvent("onTemplatesReady",function(){
   scheduler.attachEvent("onBeforeLightbox",function(id){
      if (this.config.readonly_form || this.getEvent(id).readonly)
         this.config.readonly_active = true;
      else {
         this.config.readonly_active = false;
         return true;
      }
         
      for (var i=0; i < this.config.lightbox.sections.length; i++) {
         this.config.lightbox.sections[i].focus = false;
      };
      
      return true;
   });
   
	function txt_replace(tag,d,n,text){
		var txts = d.getElementsByTagName(tag);
		var txtt = n.getElementsByTagName(tag);
		for (var i=txtt.length-1; i>=0; i--){
			var n = txtt[i];
			if (!text)
				n.disabled = true;
			else {
				var t = document.createElement("SPAN");
				t.className = "dhx_text_disabled";
				t.innerHTML=text(txts[i]);
				n.parentNode.insertBefore(t,n);
				n.parentNode.removeChild(n);   
			}
		}
	}
   
   var old = scheduler._fill_lightbox;
   scheduler._fill_lightbox=function(){
      var sns = this.config.lightbox.sections;
      if (this.config.readonly_active){
         for (var i=0; i < sns.length; i++) {
            if (sns[i].type == 'recurring') {
               var s = document.getElementById(sns[i].id);
               s.style.display=s.nextSibling.style.display='none';
               sns.splice(i,1);
               i--;
            }
         };
      }
      
      var res = old.apply(this,arguments);
      if (this.config.readonly_active){
         
         var d = this._get_lightbox();
         var n = this._lightbox_r = d.cloneNode(true);
         
         txt_replace("textarea",d,n,function(a){ return a.value; });
         txt_replace("input",d,n,false);
         txt_replace("select",d,n,function(a){ return a.options[Math.max((a.selectedIndex||0),0)].text; });
            
         n.removeChild(n.childNodes[2]);
         n.removeChild(n.childNodes[3]);
         
         d.parentNode.insertBefore(n,d);
         
         olds.call(this,n);
         this._lightbox = n;
         this.setLightboxSize();
         this._lightbox = null;
         n.onclick=function(e){
            var src=e?e.target:event.srcElement;
            if (!src.className) src=src.previousSibling;
            if (src && src.className)
               switch(src.className){
                  case "dhx_cancel_btn":
                     scheduler.callEvent("onEventCancel",[scheduler._lightbox_id]);
                     scheduler._edit_stop_event(scheduler.getEvent(scheduler._lightbox_id),false);
                     scheduler.hide_lightbox();
                     break;
               }
         };
      }
      return res;
   };
   
	var olds = scheduler.showCover;
	scheduler.showCover=function(){
		if (!this.config.readonly_active)
			olds.apply(this,arguments);
	};
   
   var hold = scheduler.hide_lightbox;
   scheduler.hide_lightbox=function(){
      if (this._lightbox_r){
         this._lightbox_r.parentNode.removeChild(this._lightbox_r);
         this._lightbox_r = null;
      }
      
      return hold.apply(this,arguments);
   };
   
   
});