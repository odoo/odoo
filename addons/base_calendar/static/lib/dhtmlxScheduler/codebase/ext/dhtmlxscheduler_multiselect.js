/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
scheduler.form_blocks.multiselect={render:function(C){var B="<div class='dhx_multi_select_"+C.name+"' style='overflow: auto; height: "+C.height+"px; position: relative;' >";for(var A=0;A<C.options.length;A++){B+="<label><input type='checkbox' value='"+C.options[A].key+"'/>"+C.options[A].label+"</label>";if(convertStringToBoolean(C.vertical)){B+="<br/>"}}B+="</div>";return B},set_value:function(C,J,I,A){var E=C.getElementsByTagName("input");for(var G=0;G<E.length;G++){E[G].checked=false}function H(M){var L=C.getElementsByTagName("input");for(var K=0;K<L.length;K++){L[K].checked=!!M[L[K].value]}}if(!scheduler._new_event){var D=[];if(I[A.map_to]){var F=I[A.map_to].split(",");for(var G=0;G<F.length;G++){D[F[G]]=true}H(D)}else{var B=document.createElement("div");B.className="dhx_loading";B.style.cssText="position: absolute; top: 40%; left: 40%;";C.appendChild(B);dhtmlxAjax.get(A.script_url+"?dhx_crosslink_"+A.map_to+"="+I.id+"&uid="+scheduler.uid(),function(K){var M=K.doXPath("//data/item");var N=[];for(var L=0;L<M.length;L++){N[M[L].getAttribute(A.map_to)]=true}H(N);C.removeChild(B)})}}},get_value:function(F,E,A){var C=[];var D=F.getElementsByTagName("input");for(var B=0;B<D.length;B++){if(D[B].checked){C.push(D[B].value)}}return C.join(",")},focus:function(A){}};