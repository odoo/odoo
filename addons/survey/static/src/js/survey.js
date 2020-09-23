odoo.define('survey.survey', function (require) {
'use strict';

require('web.dom_ready');
var core = require('web.core');
var time = require('web.time');
var ajax = require('web.ajax');
var field_utils = require('web.field_utils');
var Dialog = require('web.Dialog');

var _t = core._t;
/*
 * This file is intended to add interactivity to survey forms
 */

var the_form = $('.js_surveyform');

if(!the_form.length) {
    return Promise.reject("DOM doesn't contain '.js_surveyform'");
}

    var prefill_controller = the_form.attr("data-prefill");
    var submit_controller = the_form.attr("data-submit");
    var scores_controller = the_form.attr("data-scores");
    var print_mode = false;
    var quiz_correction_mode = false;

    // Printing mode: will disable all the controls in the form
    if (_.isUndefined(submit_controller)) {
        $(".js_surveyform .input-group-text span.fa-calendar").css("pointer-events", "none");
        $('.js_surveyform :input').prop('disabled', true);
        print_mode = true;
    }

    // Quiz correction mode
    if (! _.isUndefined(scores_controller)) {
        quiz_correction_mode = true;
    }


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
            $(this).parent().removeClass('col-lg-12').addClass('col-lg-6');
            $(this).closest('.js_drop').find('input[data-oe-survey-othert="1"]').show().focus();
        }
        else{
            $(this).parent().removeClass('col-lg-6').addClass('col-lg-12');
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

    // Pre-filling of the form with previous answers
    function prefill(){
        if (! _.isUndefined(prefill_controller)) {
            var prefill_def = $.ajax(prefill_controller, {dataType: "json"})
                .done(function(json_data){
                    _.each(json_data, function(value, key){

                        // prefill of text/number/date boxes
                        var input = the_form.find(".form-control[name=" + key + "]");
                        if (input.hasClass('datetimepicker-input')) {
                            // display dates in user timezone
                            var moment_date = field_utils.parse.date(value[0]);
                            if ($(input).closest('.input-group.date').data('questiontype') === 'datetime') {
                                value = field_utils.format.datetime(moment_date, null, {timezone: true});
                            }
                            else {
                                value = field_utils.format.date(moment_date, null, {timezone: true});
                            }
                        }
                        input.val(value);

                        // special case for comments under multiple suggestions questions
                        if (_.string.endsWith(key, "_comment") &&
                            (input.parent().hasClass("js_comments") || input.parent().hasClass("js_ck_comments"))) {
                            input.siblings().find('>input').attr("checked","checked");
                        }

                        // checkboxes and radios
                        the_form.find("input[name^='" + key + "_'][type='checkbox']").each(function(){
                            $(this).val(value);
                        });
                        the_form.find("input[name=" + key + "][type!='text']").each(function(){
                            $(this).val(value);
                        });
                    });
                })
                .fail(function(){
                    console.warn("[survey] Unable to load prefill data");
                });
            return prefill_def;
        }
    }

    // Display score if quiz correction mode
    function display_scores(){
        if (! _.isUndefined(scores_controller)) {
            var score_def = $.ajax(scores_controller, {dataType: "json"})
                .done(function(json_data){
                    _.each(json_data, function(value, key){
                        the_form.find("span[data-score-question=" + key + "]").text("Your score: " + value);
                    });
                })
                .fail(function(){
                    console.warn("[survey] Unable to load score data");
                });
            return score_def;
        }
    }

    $('.o_survey_header .breadcrumb-item a').each(function() {
        var $valObj = $(this);
        $valObj.click(function(event) {
            event.preventDefault();
            $('<input>').attr({type: 'hidden', name: 'breadcrumb_redirect', value: $valObj.attr('href')}).appendTo('.js_surveyform');
            $('.js_surveyform').submit();
        });
    });

    // Parameters for form submission
    $('.js_surveyform').ajaxForm({
        url: submit_controller,
        type: 'POST',                       // submission type
        dataType: 'json',                   // answer expected type
        beforeSubmit: function(formData, $form, options){           // hide previous errmsg before resubmitting
            var date_fields = $form.find('div.date > input.form-control');
            for (var i=0; i < date_fields.length; i++) {
                var el = date_fields[i];
                var questiontype = $(el).closest('.input-group.date').data('questiontype');
                var moment_date = questiontype === 'datetime' ? field_utils.parse.datetime(el.value, null, {timezone: true}) : field_utils.parse.date(el.value);

                var field_obj = _.findWhere(formData, {'name': el.name});
                field_obj.value = moment_date ? moment_date.toJSON() : '';
            }
            $('.js_errzone').html("").hide();
        },
        success: function(response, status, xhr, wfe){ // submission attempt
            if(_.has(response, 'errors')){  // some questions have errors
                _.each(_.keys(response.errors), function(key){
                    $("#" + key + '>.js_errzone').append($('<p>', {'text': response.errors[key]})).show();
                    if (_.keys(response.errors)[_.keys(response.errors).length - 1] === key) {
                         $('html, body').animate({
                            scrollTop: $('.js_errzone:visible:first').closest('.js_question-wrapper').offset().top - $('.o_main_navbar').height()
                        }, 500);
                    }
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
            $('#AJAXErrorModal').modal('show');
        }
    });

    function load_locale(){
        var url = "/web/webclient/locale/" + (document.documentElement.getAttribute('lang') || 'en_US').replace('-', '_');
        return ajax.loadJS(url);
    }

    // datetimepicker use moment locale to display date format according to language
    // frontend does not load moment locale at all.
    // so wait until DOM ready with locale then init datetimepicker
    load_locale().then(function(){
        _.each($('.input-group.date'), function(date_field){
            var disabledDates = [];
            var minDate, maxDate;

            // Set the datetimepicker format depending on the question type
            var datetimepickerFormat = $(date_field).data('questiontype') === 'datetime' ? time.getLangDatetimeFormat() : time.getLangDateFormat();

            // Retrieving min date & format it for datetimepicker compatibility
            if ($(date_field).data('mindate')) {
                minDate = moment(field_utils.format.datetime(moment($(date_field).data('mindate')), null, {timezone: true}), datetimepickerFormat);
            }

            // Retrieving max date & format it for datetimepicker compatibility
            if ($(date_field).data('maxdate')) {
                maxDate = moment(field_utils.format.datetime(moment($(date_field).data('maxdate')), null, {timezone: true}), datetimepickerFormat);
            }

            // Fallback in case dates are invalid or empty
            minDate = minDate ? minDate : moment({ y: 1900 });
            maxDate = maxDate ? maxDate : moment().add(200, "y");

            // Setting up maxDate & disabledDates for date-only questions
            if ($(date_field).data('questiontype') === 'date') {
                maxDate = maxDate.add(1, "d");
                disabledDates = [maxDate];
            }

            $('#' + date_field.id).datetimepicker({
                format: datetimepickerFormat,
                minDate: minDate,
                maxDate: maxDate,
                disabledDates: disabledDates,
                useCurrent: false,
                viewDate: moment(new Date()).hours(minDate.hours()).minutes(minDate.minutes()).seconds(minDate.seconds()).milliseconds(minDate.milliseconds()),
                calendarWeeks: true,
                icons: {
                    time: 'fa fa-clock-o',
                    date: 'fa fa-calendar',
                    next: 'fa fa-chevron-right',
                    previous: 'fa fa-chevron-left',
                    up: 'fa fa-chevron-up',
                    down: 'fa fa-chevron-down',
                },
                locale : moment.locale(),
                allowInputToggle: true,
                keyBinds: null,
            });
            $('#' + date_field.id).on('error.datetimepicker', function (err) {
                if (err.date) {
                    if (err.date < minDate) {
                        Dialog.alert(this, _t('The date you selected is lower than the minimum date: ') + minDate.format(datetimepickerFormat));
                    }

                    if (err.date > maxDate) {
                        Dialog.alert(this, _t('The date you selected is greater than the maximum date: ') + maxDate.format(datetimepickerFormat));
                    }
                }
                return false;
            });
        });
        // Launch prefilling
        prefill();
        if(quiz_correction_mode === true){
            display_scores();
        }
    });
});
