/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
(function(){function B(E,D,F){var G=E+"="+F+(D?("; "+D):"");document.cookie=G}function A(E){var F=E+"=";if(document.cookie.length>0){var G=document.cookie.indexOf(F);if(G!=-1){G+=F.length;var D=document.cookie.indexOf(";",G);if(D==-1){D=document.cookie.length}return document.cookie.substring(G,D)}}return""}var C=true;scheduler.attachEvent("onBeforeViewChange",function(F,E,D,I){if(C){C=false;var G=A("scheduler_settings");if(G){G=G.split("@");G[0]=this.templates.xml_date(G[0]);this.setCurrentView(G[0],G[1]);return false}}var H=this.templates.xml_format(I||E)+"@"+(D||F);B("scheduler_settings","expires=Sun, 31 Jan 9999 22:00:00 GMT",H);return true})})();