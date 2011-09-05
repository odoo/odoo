/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){
	function setCookie(name,cookie_param,value) {
		var str = name + "=" + value +  (cookie_param?("; "+cookie_param):"");
		document.cookie = str;
	}
	function getCookie(name) {
		var search = name + "=";
		if (document.cookie.length > 0) {
			var offset = document.cookie.indexOf(search);
			if (offset != -1) {
				offset += search.length;
				var end = document.cookie.indexOf(";", offset);
				if (end == -1)
					end = document.cookie.length;
				return document.cookie.substring(offset, end);
			}
		}
		return "";
	}
	var first = true;
	scheduler.attachEvent("onBeforeViewChange",function(om,od,m,d){
		if (first){
			first = false;
			var data=getCookie("scheduler_settings");
			if (data){
				data = data.split("@");
				data[0] = this.templates.xml_date(data[0]);
				this.setCurrentView(data[0],data[1]);
				return false;
			}
		}
		var text = this.templates.xml_format(d||od)+"@"+(m||om);
		setCookie("scheduler_settings","expires=Sun, 31 Jan 9999 22:00:00 GMT",text);
		return true;
	});
})();