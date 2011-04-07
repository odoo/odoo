/*
dhtmlxScheduler v.2.3

This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details

(c) DHTMLX Ltd.
*/
scheduler.attachEvent("onTemplatesReady",function(){var B=scheduler.date.str_to_date(scheduler.config.api_date);var C=scheduler.date.date_to_str(scheduler.config.api_date);var D=scheduler.templates.month_day;scheduler.templates.month_day=function(E){return"<a jump_to='"+C(E)+"' href='#'>"+D(E)+"</a>"};var A=scheduler.templates.week_scale_date;scheduler.templates.week_scale_date=function(E){return"<a jump_to='"+C(E)+"' href='#'>"+A(E)+"</a>"};dhtmlxEvent(this._obj,"click",function(E){var G=E.target||event.srcElement;var F=G.getAttribute("jump_to");if(F){scheduler.setCurrentView(B(F),"day")}})});