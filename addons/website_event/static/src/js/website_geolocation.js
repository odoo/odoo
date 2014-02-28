(function() {
    "use strict";
    function getLocation(){
        $.post( "/event/get_country_event_list/", function( data ) {
            if(data){
                $( ".country_events_list" ).replaceWith( data );
            }
        });
    }

    $(document).ready(function () {
        if($('.country_events').length){
            getLocation();
        }
    });
})();