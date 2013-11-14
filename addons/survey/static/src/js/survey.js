$(document).ready(function () {

    var the_form = $('form');
    var prefill_controller = the_form.attr("data-prefill");
    var validate_controller = the_form.attr("data-validate");
    var submit_controller = the_form.attr("data-submit");

    console.log(prefill_controller);
    console.log(validate_controller);
    console.log(submit_controller);


    // startsWith compatibility patch with old browsers
    if (typeof String.prototype.startsWith != 'function') {
        String.prototype.startsWith = function (str){
        return this.slice(0, str.length) == str;
     };
    }

    // function that display error messages
    var display_form_error = function (question_id, err_msg){
        $('#survey_' + question_id + '>.js_errzone').append('<p>' + err_msg + '</p>').show();
    };

    //$('.js_errzone').hide();

    console.debug("[survey] Custom JS for survey loaded");

    // for each question
    // check if answer exists and is not empty and is mandatory
    // check if answer type is ok
    // check if number of answers is ok
    // check if answer has good qualities

    $('form').submit(
        function(){
            console.debug("[survey] Submit button clicked");
            var answers = $('form').serializeArray();
            var valid = true;

            $('.js_errzone').html("").hide();

            $('.question-wrapper').each(
                function(){
                    var qparams = jQuery.parseJSON($(this).attr('data-oe-survey-qparams'));
                    var question_id = $(this).attr('id').slice(7);  //all the ids of question containers start with "survey_"
                    var candidate_answers = _.filter(answers, function(item){return item.name.startsWith(question_id);});
                    var answer_value;

                    if(qparams.type === 'free_text'){
                        answer_value = candidate_answers[0].value.trim();
                        if(qparams.constr_mandatory === true && answer_value === ''){
                            valid = false;
                            display_form_error(question_id, "This question is mandatory");
                        }


                    } else if (qparams.type === 'textbox'){
                        answer_value = candidate_answers[0].value.trim();
                        if(qparams.constr_mandatory === true && answer_value === ''){
                            valid = false;
                            display_form_error(question_id, "This question is mandatory");
                        }


                    } else if (qparams.type === 'numerical_box'){
                        answer_value = candidate_answers[0].value.trim();
                        if(qparams.constr_mandatory === true && answer_value === ''){
                            valid = false;
                            display_form_error(question_id, "This question is mandatory");

                        }
                        if(answer_value !== ''){
                            if(_.isNaN(parseFloat(answer_value))){
                                valid = false;
                                display_form_error(question_id, "You must answer with a number");
                           }
                        }


                    } else if (qparams.type === 'datetime'){
                        answer_value = candidate_answers[0].value.trim();
                        if(qparams.constr_mandatory === true && answer_value === ''){
                            valid = false;
                            display_form_error(question_id, "This question is mandatory");
                        }
                        if(answer_value !== ''){
                            console.warning("Date format validation is not yet implemented");
                        }

                    } else if (qparams.type === 'simple_choice_scale' || qparams.type === 'simple_choice_dropdown'){
                        if(qparams.constr_mandatory === true && _.size(candidate_answers) === 0){
                            valid = false;
                            display_form_error(question_id, "This question is mandatory");
                        }
                        // if answers:
                        // answer_value = candidate_answers[0].value;



                    } else if (qparams.type === 'multiple_choice'){
                        var answ_nbr = _.size(candidate_answers);
                        if(qparams.constr_mandatory === true && answ_nbr <= 0){
                            valid = false;
                            display_form_error(question_id, "This question is mandatory");
                        }


                    // } else if (qparams.type === 'vector'){



                    // } else if (qparams.type === 'matrix'){



                    } else {
                        console.warning('Not supported question type!');
                    }


            });

            return valid;

            // _.filter(answers, function(item){return item.name.startsWith(question_id);})
        });

});