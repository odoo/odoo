/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
scheduler.attachEvent("onTemplatesReady",function(){var C=true;var A=scheduler.date.str_to_date("%Y-%m-%d");var B=scheduler.date.date_to_str("%Y-%m-%d");scheduler.attachEvent("onBeforeViewChange",function(K,D,F,J){if(C){C=false;var E={};var G=(document.location.hash||"").replace("#","").split(",");for(var H=0;H<G.length;H++){var M=G[H].split("=");if(M.length==2){E[M[0]]=M[1]}}if(E.date||E.mode){try{this.setCurrentView((E.date?A(E.date):null),(E.mode||null))}catch(I){this.setCurrentView((E.date?A(E.date):null),F)}return false}}var L="#date="+B(J||D)+",mode="+(F||K);document.location.hash=L;return true})});