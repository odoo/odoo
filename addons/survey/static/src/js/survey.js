$(document).ready(function () {

    console.debug("[survey] Custom JS for survey is loading...");

    // Custom code for right behavior of radio buttons with comments box
    $('.js_comments>input[type="text"]').focusin(function(){
        $(this).prev().find('>input').attr("checked","checked");
    });
    $('.js_radio input[type="radio"][data-oe-survey-otherr!="1"]').click(function(){
        $(this).closest('.js_radio').find('.js_comments>input[type="text"]').val("");
    });
    $('.js_comments input[type="radio"]').click(function(){
        $(this).closest('.js_comments').find('>input[data-oe-survey-othert="1"]').focus();
    });
    // Custom code for right behavior of dropdown menu with comments
    $('.js_drop input[data-oe-survey-othert="1"]').hide();
    $('.js_drop select').change(function(){
        var other_val = $(this).find('.js_other_option').val();
        if($(this).val() === other_val){
            $(this).parent().removeClass('col-md-12').addClass('col-md-6');
            $(this).closest('.js_drop').find('input[data-oe-survey-othert="1"]').show().focus();
        }
        else{
            $(this).parent().removeClass('col-md-6').addClass('col-md-12');
            $(this).closest('.js_drop').find('input[data-oe-survey-othert="1"]').val("").hide();
        }
    });
    // Custom code for right behavior of checkboxes with comments box
    $('.js_ck_comments>input[type="text"]').focusin(function(){
        $(this).prev().find('>input').attr("checked","checked");
    });
    $('.js_ck_comments input[type="checkbox"]').change(function(){
        if (! $(this).prop("checked")){
            $(this).closest('.js_ck_comments').find('input[type="text"]').val("");
        }
    });


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

    // Parameters for form submission
    $('.js_surveyform').ajaxForm({
        url: submit_controller,
        type: 'POST',                       // submission type
        dataType: 'json',                   // answer expected type
        beforeSubmit: function(){           // hide previous errmsg before resubmitting
            $('.js_errzone').html("").hide();
        },
        success: function(response, status, xhr, wfe){ // submission attempt
            if(_.has(response, 'errors')){  // some questions have errors
                _.each(_.keys(response.errors), function(key){
                    $("#" + key + '>.js_errzone').append('<p>' + response.errors[key] + '</p>').show();
                });
                return false;
            }
            else if (_.has(response, 'redirect')){      // form is ok
                window.location.replace(response.redirect);
                return true;
            }
            else {                                      // server sends bad data
                console.error("Incorrect answer sent by server");
                return false;
            }
        },
        timeout: 5000,
        error: function(jqXHR, textStatus, errorThrown){ // failure of AJAX request
            alert("Something went wrong while contacting survey server. Your answers have probably not been recorded. Try refreshing.");
        }
    });

    // Handles the event when a question is focused out
    $('.js_question-wrapper').focusout(
        function(){
            console.debug("[survey] Focus lost on question " + $(this).attr("id"));
    });

    console.debug("[survey] Custom JS for survey loaded!");

});
