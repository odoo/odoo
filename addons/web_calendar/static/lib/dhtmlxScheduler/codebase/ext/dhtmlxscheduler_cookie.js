/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){function g(e,b,a){var c=e+"="+a+(b?"; "+b:"");document.cookie=c}function h(e){var b=e+"=";if(document.cookie.length>0){var a=document.cookie.indexOf(b);if(a!=-1){a+=b.length;var c=document.cookie.indexOf(";",a);if(c==-1)c=document.cookie.length;return document.cookie.substring(a,c)}}return""}var f=!0;scheduler.attachEvent("onBeforeViewChange",function(e,b,a,c){if(f){f=!1;var d=h("scheduler_settings");if(d)return d=d.split("@"),d[0]=this.templates.xml_date(d[0]),this.setCurrentView(d[0],
d[1]),!1}var i=this.templates.xml_format(c||b)+"@"+(a||e);g("scheduler_settings","expires=Sun, 31 Jan 9999 22:00:00 GMT",i);return!0})})();
