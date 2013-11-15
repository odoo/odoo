$(document).ready(function () {

    console.debug("[survey] Custom JS for survey is loading...");

    var the_form = $('.js_surveyform');
    var prefill_controller = the_form.attr("data-prefill");
    var validate_controller = the_form.attr("data-validate");
    var submit_controller = the_form.attr("data-submit");

    // function prefill(form){
    //     return false;
    // }

    // function validate(form){
    //     return false;
    // }

    // function submit(form){
    //     return false;
    // }

    // Parameters for form submission
    $('.js_surveyform').ajaxForm({
        url: submit_controller,
        type: 'POST',
        dataType: 'json',                 // answer expected type
        beforeSubmit: function(){
            $('.js_errzone').html("").hide();
        },
        success: function(response, status, xhr, wfe){
            if(_.has(response, 'errors')){
                _.each(_.keys(response.errors), function(key){
                    $("#" + key + '>.js_errzone').append('<p>' + response.errors[key] + '</p>').show();
                });
                return false;
            }
            else if (_.has(response, 'redirect')){
                return true;
            }
            else {
                console.error("Something bad happened during AJAX request :(");
                return false;
            }
        }
    });

    // Handles the event when a question is focused out
    $('.question-wrapper').focusout(
        function(){
            console.debug("[survey] Focus lost on question " + $(this).attr("id"));
    });

    console.debug("[survey] Custom JS for survey loaded!");

});