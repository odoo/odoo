scheduler.ical={
	parse:function(str){
		var data = str.match(RegExp(this.c_start+"[^\f]*"+this.c_end,""));
		if (!data.length) return;
		
		//unfolding 
		data[0]=data[0].replace(/[\r\n]+(?=[a-z \t])/g," ");
		//drop property
		data[0]=data[0].replace(/\;[^:\r\n]*/g,"");
		
		
		var incoming=[];
		var match;
		var event_r = RegExp("(?:"+this.e_start+")([^\f]*?)(?:"+this.e_end+")","g");
		while (match=event_r.exec(data)){
			var e={};
			var param;
			var param_r = /[^\r\n]+[\r\n]+/g;
			while (param=param_r.exec(match[1]))
				this.parse_param(param.toString(),e);
			if (e.uid && !e.id) e.id = e.uid; //fallback to UID, when ID is not defined
			incoming.push(e);	
		}
		return incoming;
	},
	parse_param:function(str,obj){
		var d = str.indexOf(":"); 
			if (d==-1) return;
		
		var name = str.substr(0,d).toLowerCase();
		var value = str.substr(d+1).replace(/\\\,/g,",").replace(/[\r\n]+$/,"");
		if (name=="summary")
			name="text";
		else if (name=="dtstart"){
			name = "start_date";
			value = this.parse_date(value,0,0);
		}
		else if (name=="dtend"){
			name = "end_date";
			if (obj.start_date && obj.start_date.getHours()==0)
				value = this.parse_date(value,24,00);
			else
				value = this.parse_date(value,23,59);
		}
		obj[name]=value;
	},
	parse_date:function(value,dh,dm){
		var t = value.split("T");	
		if (t[1]){
			dh=t[1].substr(0,2);
			dm=t[1].substr(2,2);
		}
		var dy = t[0].substr(0,4);
		var dn = parseInt(t[0].substr(4,2),10)-1;
		var dd = t[0].substr(6,2);
		if (scheduler.config.server_utc && !t[1]) { // if no hours/minutes were specified == full day event
			return new Date(Date.UTC(dy,dn,dd,dh,dm)) ;
		}
		return new Date(dy,dn,dd,dh,dm);
	},
	c_start:"BEGIN:VCALENDAR",
	e_start:"BEGIN:VEVENT",
	e_end:"END:VEVENT",
	c_end:"END:VCALENDAR"	
};