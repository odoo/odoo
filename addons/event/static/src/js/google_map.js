openerp.event = function(instance){
    instance.web.form.widgets.add('geo_address', 'instance.event.GeoAddress');
    instance.event.GoogleMapConnecter = instance.web.Class.extend({
    	init : function(){
//    		call ajex to render map load
    		
    	},
        render_map: function(address){
            var geocoder = new google.maps.Geocoder();
            geocoder.geocode( { 'address': address}, function(results, status){
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
            map_load: function() {
                var self = this;
                if(this.googleMapsLoaded.state() != "pending"){return this.googleMapsLoaded.promise();}
                    googleMapsCallback = function () {
                    self.googleMapsLoaded.resolve();
                };
                $.ajax({
                    url: "https://maps.googleapis.com/maps/api/js?v=3&callback=googleMapsCallback&sensor=false",
                    dataType: "script"
                }).fail(self.googleMapsLoaded.reject);
                return this.googleMapsLoaded.promise();
            },
            
    }),
    
    instance.event.GeoAddress = instance.web.form.Many2OneField.extend(_.extend({}, {
        init : function(){
            this._super();
            this.googleMapsLoaded = $.Deferred();
        },


        set_value:function(value){
            var self = this;
            this.get_address(value).done(function(value){
            if(!self.__parentedParent.$element.find("#address_text").length)self.__parentedParent.$element.find(".oe_td_border").after(instance.web.qweb.render("address",{'record': value}));
            var address = _.str.sprintf(' %(street)s, %(city)s, %(country_id[1])s', value);
            var defer = self.map_load();
            defer.done(function(){
                return self.render_map(address);	
            });
            });
        },
        get_address:function(value){
            if (!value || value.length == 0){
                return $.Deferred().reject();
            }
            return new instance.web.DataSet (this,this.field.relation, this.build_context()).read_ids(value[0],["street","city","country_id"]);
        },

        },
        get_value:function(){
        }

    }));
};