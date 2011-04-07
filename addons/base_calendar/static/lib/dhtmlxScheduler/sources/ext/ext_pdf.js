scheduler.toPDF=function(url,mode,header,footer){ 
	var dx = 0;
	var dy = 0;
	var colors = false;
	if (mode == "fullcolor"){
		colors = true;
		mode = "color";
	}
		
	mode = mode||"color";
	
	function x_norm(x) {
	    x = parseFloat(x);
	    if (isNaN(x)) return "auto";
	    return 100 * x / dx;
	}
	function y_norm(y) {
	    y = parseFloat(y);
	    if (isNaN(y)) return "auto";
	    return 100 * y / dy;
	}
	function xml_month_scale(xh){
		var xml="";
		for (var i = 0; i < xh.length; i++)
			xml += "\n<column><![CDATA[" + xh[i].innerHTML + "]]></column>";
		dx = xh[0].offsetWidth;
		return xml;
	}
	function de_day(node,n){ 
		var x = parseInt(node.style.left);
		
		for (var dx=0; dx < scheduler._cols.length; dx++){
			x-=scheduler._cols[dx];
			if (x<0) return dx;
		}
		return n;
	}
	function de_week(node,n){ 
		var y = parseInt(node.style.top);
		for (var dy=0; dy < scheduler._colsS.heights.length; dy++)
			if (scheduler._colsS.heights[dy]>y) return dy;
		return n;
	}
	function xml_month(yh){
		var xml="";
        var r = yh.firstChild.rows;
        for (var i = 0; i < r.length; i++) {
            var days = [];
            for (var j = 0; j < r[i].cells.length; j++){
            /*	var dd = r[i].cells[j];
            	var css = dd.className;
            	
            	if (css!=" " && css!="dhx_now ")
            		days.push("");
            	else*/
                	days.push(r[i].cells[j].firstChild.innerHTML);
            }

            xml += "\n<row height='"+yh.firstChild.rows[i].cells[0].offsetHeight+"'><![CDATA[" + days.join("|") + "]]></row>";
            dy = yh.firstChild.rows[0].cells[0].offsetHeight;
        }
        return xml;
	}
	function xml_top(profile) {
	    var xml = "<data profile='"+profile+"'";
	       if (header)
	          xml+=" header='"+header+"'";
	       if (footer)
	          xml+=" footer='"+footer+"'";
	    xml+=">";
	    xml += "<scale mode='" + scheduler._mode + "' today='" + scheduler._els.dhx_cal_date[0].innerHTML + "'>";
	    
	    if (scheduler._mode == "agenda"){
	    	var xh = scheduler._els.dhx_cal_header[0].childNodes[0].childNodes;
	    	
	    	xml+="<column>"+xh[0].innerHTML+"</column><column>"+xh[1].innerHTML+"</column>"
	    } else if (scheduler._mode == "year"){
	    	var xh = scheduler._els.dhx_cal_data[0].childNodes;
	    	for (var i=0; i < xh.length; i++) {
	    		xml+="<month label='"+xh[i].childNodes[0].innerHTML+"'>";
	    			xml+=xml_month_scale(xh[i].childNodes[1].childNodes);
	    			xml+=xml_month(xh[i].childNodes[2]);
	    		xml+="</month>";
	    	};
	    } else {
		    xml += "<x>";
		    var xh = scheduler._els.dhx_cal_header[0].childNodes;
			xml+=xml_month_scale(xh);
		    xml += "</x>";
		
		    var yh = scheduler._els.dhx_cal_data[0];
		    if (yh.firstChild.tagName == "TABLE") {
				xml += xml_month(yh);
		    } else {
				yh = yh.childNodes[yh.childNodes.length - 1];
		        while (yh.className.indexOf("dhx_scale_holder") == -1)
		            yh = yh.previousSibling;
		        yh = yh.childNodes;
		
		        xml += "<y>";
		        for (var i = 0; i < yh.length; i++)
		            xml += "\n<row><![CDATA[" + yh[i].innerHTML + "]]></row>";
		        xml += "</y>";
		        dy = yh[0].offsetHeight;
		    }
		}
		
	    xml += "</scale>";
	    return xml;
	}
	function get_style(node, style){
		return (window.getComputedStyle?(window.getComputedStyle(node, null)[style]):(node.currentStyle?node.currentStyle[style]:null))||"";
	}
	function xml_body() { 
	    var xml = "";
	    var evs = scheduler._rendered;
	    
	    if (scheduler._mode == "agenda"){
	    	for (var i=0; i < evs.length; i++)
	    	 	xml+="<event><head>"+evs[i].childNodes[0].innerHTML+"</head><body>"+evs[i].childNodes[2].innerHTML+"</body></event>";
	    } else if (scheduler._mode == "year"){
	    	var evs = scheduler.get_visible_events();
	    	for (var i=0; i < evs.length; i++) {
	    		var d = evs[i].start_date;
				if (d.valueOf()<scheduler._min_date.valueOf()) 
      				d = scheduler._min_date;
   				while (d<evs[i].end_date){
   					var m = d.getMonth()+12*(d.getFullYear()-scheduler._min_date.getFullYear())-scheduler.week_starts._month; 
   					var day  = scheduler.week_starts[m]+d.getDate()-1;

					xml+="<event day='"+(day%7)+"' week='"+Math.floor(day/7)+"' month='"+m+"'></event>";
     				scheduler._mark_year_date(d);
      				d = scheduler.date.add(d,1,"day");
      				if (d.valueOf()>=scheduler._max_date.valueOf()) 
         				break;
     			}
			}   
	    } else {
		    for (var i = 0; i < evs.length; i++) {
		        var zx = x_norm(evs[i].style.left);
		        var zy = y_norm(evs[i].style.top);
		        var zdx = x_norm(evs[i].style.width);
		        var zdy = y_norm(evs[i].style.height);
		        var e_type = evs[i].className.split(" ")[0].replace("dhx_cal_", "");
		        var dets = scheduler.getEvent(evs[i].getAttribute("event_id"))
		        var day = dets._sday;
		        var week = dets._sweek;
		        if (scheduler._mode != "month") {
		           if (parseInt(evs[i].style.left) <= 26) {
		              zx = 2;
		              zdx += x_norm(evs[i].style.left)-1;
		           }                   
		            if (evs[i].parentNode == scheduler._els.dhx_cal_data[0]) continue;
		            zx += x_norm(evs[i].parentNode.style.left);
		            zx -= x_norm(51);
		        } else {
		            zdy = parseInt(evs[i].offsetHeight);
		            zy = parseInt(evs[i].style.top) - 22;
		            
		            day = de_day(evs[i],day);
		            week = de_week(evs[i],week);
		        }
		        
		        xml += "\n<event week='"+week+"' day='"+day+"' type='" + e_type + "' x='" + zx + "' y='" + zy + "' width='" + zdx + "' height='" + zdy + "'>";
		        
		        
		        if (e_type == "event") {
		            xml += "<header><![CDATA[" + evs[i].childNodes[1].innerHTML + "]]></header>";
		            var text_color = colors?get_style(evs[i].childNodes[2],"color"):"";
		        	var bg_color = colors?get_style(evs[i].childNodes[2],"backgroundColor"):"";
		            xml += "<body backgroundColor='"+bg_color+"' color='" + text_color + "'><![CDATA[" + evs[i].childNodes[2].innerHTML + "]]></body>";
		        } else {
		            var text_color = colors?get_style(evs[i],"color"):"";
		        	var bg_color = colors?get_style(evs[i],"backgroundColor"):"";
		            xml += "<body backgroundColor='"+bg_color+"' color='" + text_color + "'><![CDATA[" + evs[i].innerHTML + "]]></body>";
		        }
		        xml += "</event>";
		    }
	    }
	    return xml;
	}
	function xml_end(){
	    var xml = "</data>";
	    return xml;
	}
	
	var uid = (new Date()).valueOf();
	var d=document.createElement("div");
	d.style.display="none";
	document.body.appendChild(d);

	d.innerHTML = '<form id="'+uid+'" method="post" target="_blank" action="'+url+'" accept-charset="utf-8" enctype="text/html"><input type="hidden" name="mycoolxmlbody"/> </form>';
	document.getElementById(uid).firstChild.value = xml_top(mode).replace("\u2013", "-") + xml_body() + xml_end();
	document.getElementById(uid).submit();
	d.parentNode.removeChild(d);grid = null;	
}   