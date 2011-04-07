

scheduler.xy.map_date_width = 188; // date column width
scheduler.xy.map_description_width = 400; // description column width

scheduler.config.map_resolve_event_location = true; // if events in database doesn't have lat and lng values there will be an attempt to resolve them on event loading, useful for migration
scheduler.config.map_resolve_user_location = true; // if user will be promted to share his location to display it on the map

scheduler.config.map_initial_position = new google.maps.LatLng(48.724, 8.215); // inital position of the map
scheduler.config.map_error_position = new google.maps.LatLng(15, 15); // this position will be displayed in case if event doesn't have corresponding coordinates

scheduler.config.map_infowindow_max_width = 300;

scheduler.config.map_type = google.maps.MapTypeId.ROADMAP;

scheduler.config.map_zoom_after_resolve = 15;

scheduler.locale.labels.marker_geo_success = "It seems you are here.";
scheduler.locale.labels.marker_geo_fail = "Sorry, could not get your current position using geolocation.";

scheduler.templates.marker_date=scheduler.date.date_to_str("%Y-%m-%d %H:%i"); // date for map's infowindow will be formated following way 

scheduler.templates.marker_text=function(start, end, ev){
	return "<div><b>"+ev.text+"</b><br/><br/>"+(ev.event_location||'')+"<br/><br/>"+scheduler.templates.marker_date(start)+" - "+scheduler.templates.marker_date(end)+"</div>";
};
scheduler.dblclick_dhx_map_area=function(){
	if (!this.config.readonly && this.config.dblclick_create)
		this.addEventNow();
};
scheduler.templates.map_time = function(start,end,ev){
	if (ev._timed) 
		return this.day_date(ev.start_date, ev.end_date, ev)+" "+this.event_date(start);
	else
		return scheduler.templates.day_date(start)+" &ndash; "+scheduler.templates.day_date(end);
};
scheduler.templates.map_text = function(ev){
	return ev.text;
};
scheduler.date.map_start=function(d){ return d; };

	
scheduler.attachEvent("onTemplatesReady",function(){

	function _append_map() {
		_isPositionSet = false; // if user actual (geolocation) position was set on the map
	
		var gmap = document.createElement('div');
		gmap.className='dhx_map';
		gmap.id='dhx_gmap';
		gmap.style.dispay = "none";
		
		node = document.getElementById('scheduler_here');

		node.appendChild(gmap);
		
		scheduler._els.dhx_gmap = [];
		scheduler._els.dhx_gmap.push(gmap);
		
		_setMapSize('dhx_gmap');

		var mapOptions = {
			zoom: scheduler.config.map_inital_zoom || 10,
			center: scheduler.config.map_initial_position,
			mapTypeId: scheduler.config.map_type||google.maps.MapTypeId.ROADMAP
		};
		map = new google.maps.Map(document.getElementById('dhx_gmap'), mapOptions);
		map.disableDefaultUI = false;
		map.disableDoubleClickZoom = true;
		
		google.maps.event.addListener(map, "dblclick", function(event) {
			if (!scheduler.config.readonly && scheduler.config.dblclick_create) {
				point = event.latLng;
				geocoder.geocode(
					{ 'latLng': point },
					function(results, status) {
						if (status == google.maps.GeocoderStatus.OK) {
							point = results[0].geometry.location;
							scheduler.addEventNow({
								lat: point.lat(), 
								lng: point.lng(), 
								event_location: results[0].formatted_address
							});
						}
					}
				);
			}	
		});
		
		var infoWindowOptions = {
			content: ''
		};

		if (scheduler.config.map_infowindow_max_width) {
			infoWindowOptions.maxWidth = scheduler.config.map_infowindow_max_width;
		}
		
		scheduler.map = {
			_points: [],
			_markers: [],
			_infowindow: new google.maps.InfoWindow(infoWindowOptions),
			_infowindows_content: [],
			_initialization_count: -1
		};
		
		geocoder = new google.maps.Geocoder();
		
		if(scheduler.config.map_resolve_user_location) {
			if(navigator.geolocation) {
				if(!_isPositionSet) {	  
					navigator.geolocation.getCurrentPosition(function(position) {
						var _userLocation = new google.maps.LatLng(position.coords.latitude,position.coords.longitude);
						map.setCenter(_userLocation);
						map.setZoom(scheduler.config.map_zoom_after_resolve||10);
						scheduler.map._infowindow.setContent(scheduler.locale.labels.marker_geo_success);
						scheduler.map._infowindow.position = map.getCenter();
						scheduler.map._infowindow.open(map);

						_isPositionSet = true;	
					}, 
					function() {
						scheduler.map._infowindow.setContent(scheduler.locale.labels.marker_geo_fail);
						scheduler.map._infowindow.setPosition(map.getCenter());
						scheduler.map._infowindow.open(map);
						_isPositionSet = true;	
					}); 
				}
			}
		}
		google.maps.event.addListener(map, "resize", function(event) {
			gmap.style.zIndex='5';	
			map.setZoom( map.getZoom() );
		});
		google.maps.event.addListener(map, "tilesloaded", function(event) {
			gmap.style.zIndex='5';	
		});
	}
	_append_map();

	scheduler.attachEvent("onSchedulerResize",function(){
	   if (this._mode == "map"){
			this.map_view(true);
	   }
	});
	
	var old = scheduler.render_data;
	scheduler.render_data=function(evs,hold){
		if (this._mode == "map") {
			fill_map_tab(); 
			var events = scheduler.get_visible_events();
			for(var i=0; i<events.length; i++) {
				if(!scheduler.map._markers[events[i].id]) {
					showAddress(events[i],false,false);
				}
			}
   	} else
   		return old.apply(this,arguments);
	};

	function set_full_view(mode){
		if (mode){
			var l = scheduler.locale.labels;
			scheduler._els["dhx_cal_header"][0].innerHTML="<div class='dhx_map_line' style='width: "+(scheduler.xy.map_date_width+scheduler.xy.map_description_width+2)+"px;' ><div style='width: "+scheduler.xy.map_date_width+"px;'>"+l.date+"</div><div class='headline_description' style='width: "+scheduler.xy.map_description_width+"px;'>"+l.description+"</div></div>";
			scheduler._table_view=true;
			scheduler.set_sizes();
		}
	}

	function fill_map_tab(){
		//get current date
		var date = scheduler._date;
		//select events for which data need to be printed
		var events = scheduler.get_visible_events();
		events.sort(function(a,b){ return a.start_date>b.start_date?1:-1; });
		
		//generate html for the view
		var html="<div class='dhx_map_area'>";
		for (var i=0; i<events.length; i++){
			var event_class = (events[i].id == scheduler._selected_event_id)?'dhx_map_line highlight':'dhx_map_line';
			html+="<div class='"+event_class+"' event_id='"+events[i].id+"' style='"+(events[i]._text_style||"")+" width: "+(scheduler.xy.map_date_width+scheduler.xy.map_description_width+2)+"px;'><div style='width: "+scheduler.xy.map_date_width+"px;' >"+scheduler.templates.map_time(events[i].start_date, events[i].end_date,events[i])+"</div>";
			html+="<div class='dhx_event_icon icon_details'>&nbsp</div>";
			html+="<div class='line_description' style='width:"+(scheduler.xy.map_description_width-25)+"px;'>"+scheduler.templates.map_text(events[i])+"</div></div>"; // -25 = icon size 20 and padding 5
		}
		html+="<div class='dhx_v_border' style='left: "+(scheduler.xy.map_date_width-2)+"px;'></div><div class='dhx_v_border_description'></div></div>";
		
		//render html
		scheduler._els["dhx_cal_data"][0].scrollTop = 0; //fix flickering in FF
		scheduler._els["dhx_cal_data"][0].innerHTML = html;
		scheduler._els["dhx_cal_data"][0].style.width = (scheduler.xy.map_date_width + scheduler.xy.map_description_width + 1) + 'px';
		
		var t=scheduler._els["dhx_cal_data"][0].firstChild.childNodes;
		scheduler._els["dhx_cal_date"][0].innerHTML="";
		
		scheduler._rendered=[];
		for (var i=0; i < t.length-2; i++) {
			scheduler._rendered[i]=t[i];
		}
		
	}
	
	function _setMapSize(elem_id) { //input - map's div id
		var map = document.getElementById(elem_id);
		map.style.height = (scheduler._y - scheduler.xy.nav_height) + 'px';
		map.style.width = (scheduler._x - scheduler.xy.map_date_width - scheduler.xy.map_description_width - 1) + 'px';
		map.style.marginLeft = (scheduler.xy.map_date_width + scheduler.xy.map_description_width + 1) + 'px';
		map.style.marginTop = (scheduler.xy.nav_height + 2) + 'px';
	}

	scheduler.map_view=function(mode){
		scheduler.map._initialization_count++;
		var gmap = scheduler._els.dhx_gmap[0];
		
		scheduler._els.dhx_cal_data[0].style.width = (scheduler.xy.map_date_width + scheduler.xy.map_description_width + 1) + 'px';
		
		scheduler._min_date = scheduler.config.map_start||(new Date());
		scheduler._max_date = scheduler.config.map_end||(new Date(9999,1,1));
		scheduler._table_view = true;
		set_full_view(mode);
		
		if (mode){ //map tab activated
			fill_map_tab();
			gmap.style.display = 'block';
			
			// need to resize block everytime window is resized
			_setMapSize('dhx_gmap');
	
			var events = scheduler.get_visible_events();
			for(var i=0; i<events.length; i++) {
				if(!scheduler.map._markers[events[i].id]) {
					showAddress(events[i]);
				}
			}
		} else { //map tab de-activated
			gmap.style.display = 'none';
		}
		
		google.maps.event.trigger(map, 'resize');
		if(scheduler.map._initialization_count === 0) { // if tab is activated for the first time need to fix position
			map.setCenter(scheduler.config.map_initial_position);
		}
	};
	
	function showAddress(event, setCenter, performClick) { // what if event have incorrect position from the start?
		if(event.lat && event.lng) {
			var point = new google.maps.LatLng(event.lat,event.lng);
		} else {
			var point = scheduler.config.map_error_position;
		}
		var message = scheduler.templates.marker_text(event.start_date, event.end_date, event);
		if(!scheduler._new_event) {
			scheduler.map._markers[event.id]= new google.maps.Marker({
				position: point,
				map: map
			});

			scheduler.map._infowindows_content[event.id] = message;

			google.maps.event.addListener(scheduler.map._markers[event.id], 'click', function() {
				scheduler.map._infowindow.setContent(scheduler.map._infowindows_content[event.id]);
				scheduler.map._infowindow.open(map,scheduler.map._markers[event.id]);
				scheduler._selected_event_id = event.id;
				scheduler.render_data();
			});

			scheduler.map._points[event.id]=point;
			
			if(setCenter) map.setCenter(scheduler.map._points[event.id]);
			if(performClick) scheduler.callEvent("onClick", [event.id]);
		}
	}
	
	scheduler.attachEvent("onClick",function(event_id, native_event_object){  
		if (this._mode == "map"){
			scheduler._selected_event_id = event_id;
			for(var i=0; i<scheduler._rendered.length; i++) {
				scheduler._rendered[i].className='dhx_map_line';
				if(scheduler._rendered[i].getAttribute("event_id") == event_id) {
					scheduler._rendered[i].className += " highlight"; 
				}
			}
			if(scheduler.map._points[event_id] && scheduler.map._markers[event_id]) {
				map.panTo(scheduler.map._points[event_id]);
				google.maps.event.trigger(scheduler.map._markers[event_id], 'click');
			}
	   }
	   return true;
	});
	
	_displayEventOnMap = function(event) {
		if (event.event_location && geocoder) { 
			geocoder.geocode(
				{ 'address': event.event_location },
				function(results, status) {
					var point = {};
					if (status != google.maps.GeocoderStatus.OK) {
						point = scheduler.callEvent("onLocationError",[event.id]);
						if (!point || point === true)
							point = scheduler.config.map_error_position;
					} else {
						point = results[0].geometry.location;
					}
					event.lat = point.lat();
					event.lng = point.lng();
					
					scheduler._selected_event_id = event.id;
					
					showAddress(event, true, true);
					dp.setUpdated(event.id, true, "updated");		
				}
			);
		} else {
			showAddress(event, true, true); 
		}
	};
	
	_updateEventLocation = function(event) { // update lat and lng in database
		if (event.event_location && geocoder) {
			geocoder.geocode(
				{ 'address': event.event_location },
				function(results, status) {
					var point = {};
					if (status != google.maps.GeocoderStatus.OK) {
						point = scheduler.callEvent("onLocationError",[event.id]);
						if (!point || point === true)
							point = scheduler.config.map_error_position;
					} else {
						point = results[0].geometry.location;
					}
					event.lat = point.lat();
					event.lng = point.lng();
					dp.setUpdated(event.id, true, "updated");
				}
			);
		}
	};
	
	_delay = function(method, object, params, delay) {
		setTimeout(function(){
			var ret = method.apply(object,params);
			method = obj = params = null;
			return ret;
		},delay||1000);	
	};
	
	scheduler.attachEvent("onEventChanged", function(event_id,event_object){
		if(scheduler.is_visible_events(scheduler.getEvent(event_id))) {
			scheduler.map._markers[event_id].setMap(null);
			var event = scheduler.getEvent(event_id);
			_displayEventOnMap(event);
		} else {
			scheduler.map._infowindow.close();
			scheduler.map._markers[event_id].setMap(null);
		}
		return true;
   });
	
	scheduler.attachEvent("onEventIdChange", function(old_event_id,new_event_id){
		if(scheduler.is_visible_events(scheduler.getEvent(new_event_id))) {
			if(scheduler.map._markers[old_event_id]) scheduler.map._markers[old_event_id].setMap(null); 
			var event = scheduler.getEvent(new_event_id);
			_displayEventOnMap(event);
		}
		return true;
	});
	
	/* Test/example
	scheduler.attachEvent("onLocationError", function(event_id,event_object){
		return new google.maps.LatLng(8, 8);
   });
	*/
	
	scheduler.attachEvent("onBeforeEventDelete", function(event_id,event_object){
			if (scheduler.map._markers[event_id]) {
				scheduler.map._markers[event_id].setMap(null); // if new event is deleted tab != map then it doesn't have marker yet
			}
			scheduler.map._infowindow.close();
		return true;
   });
	
	scheduler._event_resolve_delay = 500;
	scheduler.attachEvent("onEventLoading", function(event){	
		if(scheduler.config.map_resolve_event_location && event.event_location && !event.lat && !event.lng) { // don't delete !event.lat && !event.lng as location could change
			scheduler._event_resolve_delay += 500;
			_delay(_updateEventLocation,this,[event], scheduler._event_resolve_delay);
		}
		return true;
   });
	
	scheduler.attachEvent("onEventCancel", function(event_id, is_new){
		if(is_new) {
			if(scheduler.map._markers[event_id]) 
				scheduler.map._markers[event_id].setMap(null);
			scheduler.map._infowindow.close();
		}
		return true;
   });
});