/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
scheduler.data_attributes=function(){var f=[],d=scheduler.templates.xml_format,c;for(c in this._events){var e=this._events[c],a;for(a in e)a.substr(0,1)!="_"&&f.push([a,a=="start_date"||a=="end_date"?d:null]);break}return f};
scheduler.toXML=function(f){var d=[],c=this.data_attributes(),e;for(e in this._events){var a=this._events[e];if(a.id.toString().indexOf("#")==-1){d.push("<event>");for(var b=0;b<c.length;b++)d.push("<"+c[b][0]+"><![CDATA["+(c[b][1]?c[b][1](a[c[b][0]]):a[c[b][0]])+"]]\></"+c[b][0]+">");d.push("</event>")}}return(f||"")+"<data>"+d.join("\n")+"</data>"};
scheduler.toJSON=function(){var f=[],d=this.data_attributes(),c;for(c in this._events){var e=this._events[c];if(e.id.toString().indexOf("#")==-1){for(var e=this._events[c],a=[],b=0;b<d.length;b++)a.push(" "+d[b][0]+':"'+((d[b][1]?d[b][1](e[d[b][0]]):e[d[b][0]])||"").toString().replace(/\n/g,"")+'" ');f.push("{"+a.join(",")+"}")}}return"["+f.join(",\n")+"]"};
scheduler.toICal=function(f){var d="BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//dhtmlXScheduler//NONSGML v2.2//EN\nDESCRIPTION:",c="END:VCALENDAR",e=scheduler.date.date_to_str("%Y%m%dT%H%i%s"),a=[],b;for(b in this._events){var g=this._events[b];g.id.toString().indexOf("#")==-1&&(a.push("BEGIN:VEVENT"),a.push("DTSTART:"+e(g.start_date)),a.push("DTEND:"+e(g.end_date)),a.push("SUMMARY:"+g.text),a.push("END:VEVENT"))}return d+(f||"")+"\n"+a.join("\n")+"\n"+c};
