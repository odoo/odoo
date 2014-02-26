(function() {
    "use strict";
    function getLocation()
    {
        if (navigator.geolocation)
        {
            navigator.geolocation.getCurrentPosition(showPosition);
        }
        else{alert("Geolocation is not supported by this browser.");}
    }
    
    function showPosition(position)
    {
        var latitude = position.coords.latitude;
        var longitude = position.coords.longitude;
        $.ajax({
            url:  "https://maps.googleapis.com/maps/api/geocode/json?latlng="+latitude+","+longitude+"&sensor=false",
            type: 'GET',
            dataType: 'json',
            success: function(response, status, xhr, wfe){ 
                if(response.status == 'OK'){
                    var last_element = response.results[response.results.length - 1]
                    if( last_element.types.indexOf( "country" ) != -1){
                        var country_obj = last_element.address_components[0];
                        $('img.event_country_flag').attr('src','base/static/img/country_flags/'+country_obj.short_name.toLowerCase()+'.png');
                        $.post( "/event/get_country_event_list/"+country_obj.short_name, function( data ) {
                            $( ".country_events_list" ).replaceWith( data );
                        });
                    }
                }
            }
        });
    }

    $(document).ready(function () {
        if($('.country_events').length){
            getLocation();
        }
    });
})();