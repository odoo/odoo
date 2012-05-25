openerp.event = function(instance, mod) {
    instance.web.form.widgets.add('many2one_address_google_map', 'instance.event.Many2OneAddress');

    instance.google_map.GoogleMapConnector = instance.web.Class.extend({
        init: function(){
            this.googleMapsLoaded = $.Deferred();
            this.map_load();
        },
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
        render_map: function(address,$element){
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
                    map : new google.maps.Map($element,myOptions),
                    position: new google.maps.LatLng(lat,lng)
                });
                }
            });
        },
    });
    instance.google_map.Many2OneAddress = instance.web.form.FieldMany2One.extend({
        init: function(field_manager, node){
          this._super(field_manager, node);
          this.map = new instance.google_map.GoogleMapConnector(); 
        },
        get_address:function(value){
            var self = this;
            if (!value || value.length == 0){
                return $.Deferred().reject();
            }
            (value instanceof Array)?value = parseInt(value[0]):false;
            var data = new instance.web.DataSet(this,this.field.relation, this.build_context());
            data.read_ids(value,["street","city","zip","country_id"]).done(function(value){
                var address;
                if value['country_id'] {
                    address = _.str.sprintf('%(street)s, %(zip)s %(city)s, %(country_id[1])s', value);
                } else {
                    address = _.str.sprintf('%(street)s, %(zip)s %(city)s', value);
                }
                self.map.googleMapsLoaded.done(function(){
                    self.map.render_map(address,self.$(self.options.selector)[0]);
                })
            });
        },
        set_value:function(value){
            this._super(value);
            this.get_address(value);
        },
        render_value:function(no_recurse){
            this.get_address(this.get("value"));
            this._super(no_recurse);
        }
    });
};
