/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTemplatesReady",function(){var d=!0,e=scheduler.date.str_to_date("%Y-%m-%d"),h=scheduler.date.date_to_str("%Y-%m-%d");scheduler.attachEvent("onBeforeViewChange",function(i,j,f,k){if(d){d=!1;for(var a={},g=(document.location.hash||"").replace("#","").split(","),b=0;b<g.length;b++){var c=g[b].split("=");c.length==2&&(a[c[0]]=c[1])}if(a.date||a.mode){try{this.setCurrentView(a.date?e(a.date):null,a.mode||null)}catch(m){this.setCurrentView(a.date?e(a.date):null,f)}return!1}}var l=
"#date="+h(k||j)+",mode="+(f||i);document.location.hash=l;return!0})});
