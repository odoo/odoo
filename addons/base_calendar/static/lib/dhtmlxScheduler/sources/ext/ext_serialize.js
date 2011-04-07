//redefine this method, if you want to provide a custom set of attributes for serialization
scheduler.data_attributes=function(){
	var attrs = [];
	var format = scheduler.templates.xml_format;
	for (var a in this._events){
		var ev = this._events[a];
		for (var name in ev)
			if (name.substr(0,1) !="_")
				attrs.push([name,((name == "start_date" || name == "end_date")?format:null)]);
		break;
	}
	return attrs;
}

scheduler.toXML = function(header){
	var xml = [];
	var attrs = this.data_attributes();
	
	
	for (var a in this._events){
		var ev = this._events[a];
		if (ev.id.toString().indexOf("#")!=-1) continue;
		xml.push("<event>");	
		for (var i=0; i < attrs.length; i++)
			xml.push("<"+attrs[i][0]+"><![CDATA["+(attrs[i][1]?attrs[i][1](ev[attrs[i][0]]):ev[attrs[i][0]])+"]]></"+attrs[i][0]+">");
			
		xml.push("</event>");
	}
	return (header||"")+"<data>"+xml.join("\n")+"</data>";
};

scheduler.toJSON = function(){
	var json = [];
	var attrs = this.data_attributes();
	for (var a in this._events){
		var ev = this._events[a];
		if (ev.id.toString().indexOf("#")!=-1) continue;
		var ev = this._events[a];
		var line =[];	
		for (var i=0; i < attrs.length; i++)
			line.push(' '+attrs[i][0]+':"'+((attrs[i][1]?attrs[i][1](ev[attrs[i][0]]):ev[attrs[i][0]])||"").toString().replace(/\n/g,"")+'" ');
		json.push("{"+line.join(",")+"}");
	}
	return "["+json.join(",\n")+"]";
};


scheduler.toICal = function(header){
	var start = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//dhtmlXScheduler//NONSGML v2.2//EN\nDESCRIPTION:";
	var end = "END:VCALENDAR";
	var format = scheduler.date.date_to_str("%Y%m%dT%H%i%s");
		
	var ical = [];
	for (var a in this._events){
		var ev = this._events[a];
		if (ev.id.toString().indexOf("#")!=-1) continue;
		
		
		ical.push("BEGIN:VEVENT");	
		ical.push("DTSTART:"+format(ev.start_date));	
		ical.push("DTEND:"+format(ev.end_date));	
		ical.push("SUMMARY:"+ev.text);	
		ical.push("END:VEVENT");
	}
	return start+(header||"")+"\n"+ical.join("\n")+"\n"+end;
};