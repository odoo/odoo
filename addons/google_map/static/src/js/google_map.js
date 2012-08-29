openerp.event = function(instance, mod) {
    instance.web.form.widgets.add('many2one_address_google_map', 'instance.google_map.Many2OneAddress');

    var googleMapsLoaded = null;

    instance.google_map.GoogleMapConnector = instance.web.Class.extend({
        map_load: function() {
            var self = this;
            if(googleMapsLoaded === null) {
                googleMapsLoaded = $.Deferred();
                // global
                openerp_googleMapsCallback = googleMapsLoaded.resolve;
                $.ajax({
                    url: "https://maps.googleapis.com/maps/api/js?v=3&callback=openerp_googleMapsCallback&sensor=false",
                    dataType: "script"
                }).fail(googleMapsLoaded.reject);
            }
            return googleMapsLoaded;
        },
        render_map: function(address,element) {
            this.map_load().then(function() {
                var geocoder = new google.maps.Geocoder();
                geocoder.geocode({'address': address}, function(results, status) {
                    if (status == google.maps.GeocoderStatus.OK) {
                        var lat = results[0].geometry.location.lat();
                        var lng = results[0].geometry.location.lng();
                        var myOptions = {
                            zoom: 17,
                            center: new google.maps.LatLng(lat,lng),
                            mapTypeId: google.maps.MapTypeId.ROADMAP
                        };
                        var map = new google.maps.Map(element,myOptions);
                        var position = new google.maps.LatLng(lat,lng);
                        var marker = new google.maps.Marker({ map: map, position: position });
                        return marker;
                    }
                });
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
                if (value['country_id']) {
                    address = _.str.sprintf('%(street)s, %(zip)s %(city)s, %(country_id[1])s', value);
                } else {
                    address = _.str.sprintf('%(street)s, %(zip)s %(city)s', value);
                }
                // TODO repalce by widget_option selector self.options.selector
                var el = self.view.$el.find(".oe_google_map")[0];
                self.map.render_map(address,el);
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
