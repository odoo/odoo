$(document).ready(function() {

    jQuery.expr[":"].Contains = jQuery.expr.createPseudo(function(arg) {
        return function( elem ) {
            return jQuery(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0;
        };
    });

    $("#event_track_search").bind('keyup', function(e){
        var change_text = $(this).val();
        $('.event_track').removeClass('invisible');

        $("#search_summary").removeClass('invisible');
        if (change_text) {
            $("#search_number").text($(".event_track:Contains("+change_text+")").length);
            $(".event_track:not(:Contains("+change_text+"))").addClass('invisible');
        } else {
            $("#search_number").text(30);
        }

        event.preventDefault();
    });

});
