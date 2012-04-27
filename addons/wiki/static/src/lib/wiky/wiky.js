/**
 * Wiky.js - Javascript library to converts Wiki MarkUp language to HTML.
 * You can do whatever with it. Please give me some credits (Apache License)
 * - Tanin Na Nakorn 
 */

var wiky = {};


wiky.process = function(wikitext) {
	var lines = wikitext.split(/\r?\n/);
	var start;
	var html = "";
	for (var i=0;i<lines.length;i++)
	{
		var line = lines[i];
		if (line.match(/^===/)!=null && line.match(/===$/)!=null)
		{
			html += "<h3>"+line.substring(3,line.length-3)+"</h3>";
		}
		else if (line.match(/^==/)!=null && line.match(/==$/)!=null)
		{
			html += "<h2>"+line.substring(2,line.length-2)+"</h2>";
		}
		else if (line.match(/^=/)!=null && line.match(/=$/)!=null)
		{
			html += "<h1>"+line.substring(1,line.length-1)+"</h1>";
		}
		else if (line.match(/^:+/)!=null)
		{
			// find start line and ending line
			start = i;
			while (i < lines.length && lines[i].match(/^:+/)!=null) i++;
			i--;
			
			html += wiky.process_indent(lines,start,i);
		}
		else if (line.match(/^----+(\s*)$/)!=null)
		{
			html += "<hr/>";
		}
		else if (line.match(/^(\*+) /)!=null)
		{
			// find start line and ending line
			start = i;
			while (i < lines.length && lines[i].match(/^(\*+|##+):? /)!=null) i++;
			i--;
			
			html += wiky.process_bullet_point(lines,start,i);
		}
		else if (line.match(/^(#+) /)!=null)
		{
			// find start line and ending line
			start = i;
			while (i < lines.length && lines[i].match(/^(#+|\*\*+):? /)!=null) i++;
			i--;
			
			html += wiky.process_bullet_point(lines,start,i);
		}
		else if (line.match(/^img:/)!=null)
		{
			html += wiky.process_image(line.substring(4));
		}
		else if (line.match(/^attach:/)!=null)
		{
			html += "<a href='"+line.substring(7)+"'>Download the file</a>"
		}
		else 
		{
			html += wiky.process_normal(line);
		}
		
		html += "<br/>\n";
	}
	return html;
};

wiky.process_indent = function(lines,start,end) {
	var html = "<dl>";
	
	for(var i=start;i<=end;i++) {
		
		html += "<dd>";
		
		var this_count = lines[i].match(/^(:+)/)[1].length;
		
		html += wiky.process_normal(lines[i].substring(this_count));
		
		var nested_end = i;
		for (var j=i+1;j<=end;j++) {
			var nested_count = lines[j].match(/^(:+)/)[1].length;
			if (nested_count <= this_count) break;
			else nested_end = j;
		}
		
		if (nested_end > i) {
			html += wiky.process_indent(lines,i+1,nested_end);
			i = nested_end;
		}
		
		html += "</dd>";
	}
	
	html += "</dl>";
	return html;
};

wiky.process_bullet_point = function(lines,start,end) {
	var html = (lines[start].charAt(0)=='*')?"<ul>":"<ol>";
	for(var i=start;i<=end;i++) {
		
		html += "<li>";
		
		var this_count = lines[i].match(/^(\*+|#+) /)[1].length;
		
		html += wiky.process_normal(lines[i].substring(this_count+1));
		
		// continue previous with #:
		{
			var nested_end = i;
			for (var j = i + 1; j <= end; j++) {
				var nested_count = lines[j].match(/^(\*+|#+):? /)[1].length;
				
				if (nested_count < this_count) 
					break;
				else {
					if (lines[j].charAt(nested_count) == ':') {
						html += "<br/>" + wiky.process_normal(lines[j].substring(nested_count + 2));
						nested_end = j;
					} else {
						break;
					}
				}
					
			}
			
			i = nested_end;
		}
		
		// nested bullet point
		{
			var nested_end = i;
			for (var j = i + 1; j <= end; j++) {
				var nested_count = lines[j].match(/^(\*+|#+):? /)[1].length;
				if (nested_count <= this_count) 
					break;
				else 
					nested_end = j;
			}
			
			if (nested_end > i) {
				html += wiky.process_bullet_point(lines, i + 1, nested_end);
				i = nested_end;
			}
		}
		
		// continue previous with #:
		{
			var nested_end = i;
			for (var j = i + 1; j <= end; j++) {
				var nested_count = lines[j].match(/^(\*+|#+):? /)[1].length;
				
				if (nested_count < this_count) 
					break;
				else {
					if (lines[j].charAt(nested_count) == ':') {
						html += wiky.process_normal(lines[j].substring(nested_count + 2));
						nested_end = j;
					} else {
						break;
					}
				}
					
			}
			
			i = nested_end;
		}
		
		html += "</li>";
	}
	
	html += (lines[start].charAt(0)=='*')?"</ul>":"</ol>";
	return html;
};

wiky.process_url = function(txt) {
	
	var index = txt.indexOf(" ");
	
	if (index == -1) 
	{
		return "<a target='"+txt+"' href='"+txt+"' style='background: url(\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAFZJREFUeF59z4EJADEIQ1F36k7u5E7ZKXeUQPACJ3wK7UNokVxVk9kHnQH7bY9hbDyDhNXgjpRLqFlo4M2GgfyJHhjq8V4agfrgPQX3JtJQGbofmCHgA/nAKks+JAjFAAAAAElFTkSuQmCC\") no-repeat scroll right center transparent;padding-right: 13px;'></a>";
	}
	else
	{
		var url = txt.substring(0,index);
		var label = txt.substring(index+1);
		return "<a target='"+url+"' href='"+url+"' style='background: url(\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAFZJREFUeF59z4EJADEIQ1F36k7u5E7ZKXeUQPACJ3wK7UNokVxVk9kHnQH7bY9hbDyDhNXgjpRLqFlo4M2GgfyJHhjq8V4agfrgPQX3JtJQGbofmCHgA/nAKks+JAjFAAAAAElFTkSuQmCC\") no-repeat scroll right center transparent;padding-right: 13px;'>"+label+"</a>";
	}
};

wiky.process_image = function(txt) {
	var index = txt.indexOf(" ");
	var url = txt;
	var label = "";
	
	if (index > -1) 
	{
		label = txt.substring(0,index);
		url = txt.substring(index+1);
	}
	return "<img src='"+url+"' alt=\""+label+"\" />";
};

wiky.process_video = function(url) {

	if (url.match(/^(https?:\/\/)?(www.)?youtube.com\//) == null)
	{
		return "<b>"+url+" is an invalid YouTube URL</b>";
	}
	var result;
	if ((result = url.match(/^(https?:\/\/)?(www.)?youtube.com\/watch\?(.*)v=([^&]+)/)) != null)
	{
		url = "http://www.youtube.com/embed/"+result[4];
	}
	
	
	return '<iframe width="480" height="390" src="'+url+'" frameborder="0" allowfullscreen></iframe>';
};

wiky.process_normal = function(wikitext) {
	
	// Image
	{
		var index = wikitext.indexOf("[[File:");
		var end_index = wikitext.indexOf("]]", index + 7);
		while (index > -1 && end_index > -1) {
			
			wikitext = wikitext.substring(0,index) 
						+ wiky.process_image(wikitext.substring(index+7,end_index)) 
						+ wikitext.substring(end_index+2);
		
			index = wikitext.indexOf("[[File:");
			end_index = wikitext.indexOf("]]", index + 7);
		}
	}
	
	// Video
	{
		var index = wikitext.indexOf("[[Video:");
		var end_index = wikitext.indexOf("]]", index + 8);
		while (index > -1 && end_index > -1) {
			
			wikitext = wikitext.substring(0,index) 
						+ wiky.process_video(wikitext.substring(index+8,end_index)) 
						+ wikitext.substring(end_index+2);
		
			index = wikitext.indexOf("[[Video:");
			end_index = wikitext.indexOf("]]", index + 8);
		}
	}
	
	
	// URL
	var protocols = ["http","ftp","news"];
	
	for (var i=0;i<protocols.length;i++)
	{
		var index = wikitext.indexOf("["+protocols[i]+"://");
		var end_index = wikitext.indexOf("]", index + 1);
		while (index > -1 && end_index > -1) {
		
			wikitext = wikitext.substring(0,index) 
						+ wiky.process_url(wikitext.substring(index+1,end_index)) 
						+ wikitext.substring(end_index+1);
		
			index = wikitext.indexOf("["+protocols[i]+"://",end_index+1);
			end_index = wikitext.indexOf("]", index + 1);
			
		}
	}
	
	var count_b = 0;
	var index = wikitext.indexOf("'''");
	while(index > -1) {
		
		if ((count_b%2)==0) wikitext = wikitext.replace(/'''/,"<b>");
		else wikitext = wikitext.replace(/'''/,"</b>");
		
		count_b++;
		
		index = wikitext.indexOf("'''",index);
	}
	
	var count_i = 0;
	var index = wikitext.indexOf("''");
	while(index > -1) {
		
		if ((count_i%2)==0) wikitext = wikitext.replace(/''/,"<i>");
		else wikitext = wikitext.replace(/''/,"</i>");
		
		count_i++;
		
		index = wikitext.indexOf("''",index);
	}
	
	wikitext = wikitext.replace(/<\/b><\/i>/g,"</i></b>");
	
	return wikitext;
};
