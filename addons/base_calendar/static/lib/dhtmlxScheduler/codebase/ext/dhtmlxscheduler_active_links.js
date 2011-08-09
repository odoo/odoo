/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.attachEvent("onTemplatesReady",function(){var d=scheduler.date.str_to_date(scheduler.config.api_date),b=scheduler.date.date_to_str(scheduler.config.api_date),e=scheduler.templates.month_day;scheduler.templates.month_day=function(a){return"<a jump_to='"+b(a)+"' href='#'>"+e(a)+"</a>"};var f=scheduler.templates.week_scale_date;scheduler.templates.week_scale_date=function(a){return"<a jump_to='"+b(a)+"' href='#'>"+f(a)+"</a>"};dhtmlxEvent(this._obj,"click",function(a){var b=a.target||event.srcElement,
c=b.getAttribute("jump_to");if(c)return scheduler.setCurrentView(d(c),"day"),a&&a.preventDefault&&a.preventDefault(),!1})});
