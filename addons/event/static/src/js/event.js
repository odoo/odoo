openerp.event = function(instance){
	instance.web.form.widgets.add('geo_address', 'instance.event.GeoAddress');
	instance.event.GeoAddress = instance.web.form.AbstractField.extend(_.extend({}, {

		init : function(){
			this._super.apply(this,arguments);
		},

		start:function(){
		},
		
	 	set_input_id:function(id){
	 	},
	 	set_value:function(value){
	 		var self = this;
			this.get_address(value).done(function(value){
				self.__parentedParent.$element.find(".oe_td_border").after(instance.web.qweb.render("address",{'record': value}));
				var address = _.str.sprintf(' %(street)s, %(city)s, %(country_id[1])s', value);
				return self.list_addresses(address);
				
			});
			
	 	},
	 	get_address:function(value){
	 		if (!value || value.length == 0){
	 			return $.Deferred().reject();
	 		}
			return new instance.web.DataSet (this,this.field.relation, this.build_context()).read_ids(value[0],["street","city","country_id"]);
	 	},

	 	list_addresses: function(address){
	 		var geocoder = new google.maps.Geocoder();
			geocoder.geocode( { 'address': address}, function(results, status) 
			{
			if (status == google.maps.GeocoderStatus.OK){
				var lat = results[0].geometry.location.lat(),lng =results[0].geometry.location.lng();
				var myOptions = {       
					zoom: 17,       
					center:  new google.maps.LatLng(lat,lng),       
					mapTypeId: google.maps.MapTypeId.ROADMAP     
				}
		    	return new google.maps.Marker({
				    map : new google.maps.Map(document.getElementById("oe_mapbox"),myOptions),
				    position: new google.maps.LatLng(lat,lng)
			 	 });
	 		}
			});
			
	 	},
	 	get_value:function(){
	 	}
		
	}));
};