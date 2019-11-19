odoo.define('survey.form', function(require) {
'use strict';

var ajax = require('web.ajax');
var field_utils = require('web.field_utils');
var publicWidget = require('web.public.widget');
var time = require('web.time');

publicWidget.registry.SurveyFormWidget = publicWidget.Widget.extend({
    selector: '.o_survey_form',
    events: {
        'change .o_survey_form_choice_item': '_onChangeChoiceItem',
        'click button[type="submit"]': '_onSubmit',
        'click .o_survey_header .breadcrumb-item a': '_onBreadcrumbClick',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            self.options = self.$target.find('form').data()
            var $timer = $('.o_survey_timer');
            if ($timer.length) {
                var timeLimitMinutes = self.options.timeLimitMinutes;
                var timer = self.options.timer;
                self.surveyTimerWidget = new publicWidget.registry.SurveyTimerWidget(self, {
                    'timer': timer,
                    'timeLimitMinutes': timeLimitMinutes
                });
                self.surveyTimerWidget.attachTo($timer);
                self.surveyTimerWidget.on('time_up', self, function (ev) {
                    self.$el.find('button[type="submit"]').click();
                });
            }
            self.$('div.o_survey_form_date').each(function () {
                self._initDateTimePicker($(this));
            });
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    // Handlers
    // -------------------------------------------------------------------------

    /*
    * Checks, if the 'other' choice is checked. Applies only if the comment count as answer.
    * In case of dropdownlist:
    *   If not checked : Clear the comment textarea and hide it
    *   If checked : show the comment textarea and focus on it
    * In case of radio buttons
    *   If not checked : Clear the comment textarea and disable it
    *   If checked : enable the comment textarea and focus on it
    *
    * @private
    * @param {Event} event
    */
    _onChangeChoiceItem: function (event) {
        var $choiceItemGroup = $(event.currentTarget).parents('.o_survey_form_choice');
        var $otherItem = $choiceItemGroup.find('.o_survey_js_form_other_comment');
        var $commentInput = $choiceItemGroup.find('textarea[type="text"]');

        // Handle dropdownlist
        var $dropdownlist = $choiceItemGroup.find('select');
        var isDropdown = $dropdownlist.length > 0

        var isOtherSelected = (isDropdown && $dropdownlist.val() === $otherItem.val()) || $otherItem.prop('checked')

        if (isOtherSelected || $commentInput.hasClass('o_survey_comment')) {
            if (isDropdown) {
                $commentInput.toggleClass('d-none', false);
            }
            if (isOtherSelected) {
                $commentInput.enable();
                $commentInput.focus();
            }
        } else {
            if (isDropdown) {
                $commentInput.toggleClass('d-none', true);
            }
            $commentInput.val('');
            $commentInput.enable(false);
        }
    },

    /*
    * When clicking on a breadcrumb enabled item, redirect to the target page.
    * Uses the submit flow to validate and save the answer before going to the specified page.
    *
    * @private
    * @param {Event} event
    */
    _onBreadcrumbClick: function (event) {
        event.preventDefault();
        this._submitForm({'previous_page_id': $(event.currentTarget).data('previousPageId')})
    },

    _onSubmit: function (event) {
        event.preventDefault();
        if ($(event.currentTarget).val() === 'previous') {
            this._submitForm({'previous_id': $(event.currentTarget).data('previousId')});
        } else {
            this._submitForm({});
        }
    },

    _submitForm: function (params) {
        var self = this;
        var $form = this.$('form');
        var formData = new FormData($form[0]);

        this._prepareSubmitValues(formData, params);

        this._resetErrors();

        return self._rpc({
            route: '/survey/submit/' + self.options.surveyToken + '/' + self.options.answerToken ,
            params: params,
        }).then(function (result) {
            return self._onSubmitDone(result, params);
        });
    },

    _onSubmitDone: function (result, params) {
        var self = this;
        if (result && !result.error) {
            window.location = result;
        }
        else if (result && result.fields && result.error === 'validation') {
            var fieldKeys = _.keys(result.fields);
            _.each(fieldKeys, function (key) {
                self.$("#" + key + '>.o_survey_question_error').append($('<p>', {text: result.fields[key]})).toggleClass('d-none', false);
                if (fieldKeys[fieldKeys.length - 1] === key) {
                    self._scrollToError(self.$('.o_survey_question_error:visible:first').closest('.js_question-wrapper'));
                }
            });
            return false;
        }
        else {
            var $target = self.$('.o_survey_error');
            $target.toggleClass('d-none', false);
            self._scrollToError($target);
            return false;
        }
    },

    // PREPARE SUBMIT TOOLS
    // -------------------------------------------------------------------------
    /*
    * For each type of question, extract the answer from inputs or textarea (comment or answer)
    *
    *
    * @private
    * @param {Event} event
    */
    _prepareSubmitValues: function (formData, params) {
        var self = this;
        // Get all context params -- TODO : Use formData instead (test if input with no name are in formData)
        formData.forEach(function(value, key){
            switch (key) {
                case 'csrf_token':
                case 'token':
                case 'page_id':
                case 'question_id':
                    params[key] = value;
                    break;
            }
        });

        // Get all question answers by question type
        this.$('[data-question-type]').each(function () {
            switch ($(this).data('questionType')) {
                case 'free_text':
                case 'textbox':
                case 'numerical_box':
                    params[this.name] = this.value;
                    break;
                case 'date':
                    params = self._prepareSubmitDates(params, this.name, this.value, false);
                    break;
                case 'datetime':
                    params = self._prepareSubmitDates(params, this.name, this.value, true);
                    break;
                case 'simple_choice_dropdown':
                    params = self._prepareSubmitChoices(params, $(this), $(this).data('name'), 'option:selected');
                    break;
                case 'simple_choice_radio':
                case 'multiple_choice':
                    params = self._prepareSubmitChoices(params, $(this), $(this).data('name'), 'input:checked');
                    break;
                case 'matrix':
                    params = self._prepareSubmitAnswersMatrix(params, $(this));
                    break;
            }
        });
    },

    /**
    *   Prepare date answer before submitting form.
    *   Convert date value from client current timezone to UTC Date to correspond to the server format.
    *   return params = { 'dateQuestionId' : '2019-05-23', 'datetimeQuestionId' : '2019-05-23 14:05:12' }
    */
    _prepareSubmitDates: function(params, questionId, value, isDateTime) {
        var momentDate = isDateTime ? field_utils.parse.datetime(value, null, {timezone: true}) : field_utils.parse.date(value);
        var formattedDate = momentDate ? momentDate.toJSON() : '';
        params[questionId] = formattedDate;
        return params;
    },

    /**
    *   Prepare choice answer before submitting form.
    *   If the answer is not the 'comment selection' (=Other), calls the _prepareSubmitAnswer method to add the answer to the params
    *   If there is a comment linked to that question, calls the _prepareSubmitComment method to add the comment to the params
    */
    _prepareSubmitChoices: function(params, $parent, questionId, selector) {
        var self = this;
        $parent.find(selector).each(function () {
            if (this.value != '-1') {
                params = self._prepareSubmitAnswer(params, questionId, this.value);
            }
        });
        params = self._prepareSubmitComment(params, $parent, questionId, false);
        return params;
    },


    /**
    *   Prepare matrix answers before submitting form.
    *   This method adds matrix answers one by one and add comment if any to a params key,value like :
    *   params = { 'matrixQuestionId' : {'rowId1': [colId1, colId2,...], 'rowId2': [colId1, colId3, ...], 'comment': comment }}
    */
    _prepareSubmitAnswersMatrix: function(params, $matrixDiv) {
        var self = this;
        $matrixDiv.find('input:checked').each(function () {
            params = self._prepareSubmitAnswerMatrix(params, $matrixDiv.data('name'), $(this).data('rowId'), this.value);
        });
        params = self._prepareSubmitComment(params, $matrixDiv, $matrixDiv.data('name'), true);
        return params;
    },

    /**
    *   Prepare answer before submitting form if question type is matrix.
    *   This method regroups answers by question and by row to make an object like :
    *   params = { 'matrixQuestionId' : { 'rowId1' : [colId1, colId2,...], 'rowId2' : [colId1, colId3, ...] } }
    */
    _prepareSubmitAnswerMatrix: function(params, questionId, rowId, colId) {
        var value = questionId in params ? params[questionId] : {};
        if (rowId in value) {
            value[rowId].push(colId);
        } else {
            value[rowId] = [colId];
        }
        params[questionId] = value;
        return params;
    },

    /**
    *   Prepare answer before submitting form (any kind of answer - except Matrix -).
    *   This method regroups answers by question.
    *   Lonely answer are directly assigned to questionId. Multiple answers are regrouped in an array:
    *   params = { 'questionId1' : lonelyAnswer, 'questionId2' : [multipleAnswer1, multipleAnswer2, ...] }
    */
    _prepareSubmitAnswer: function(params, questionId, value) {
        if (questionId in params) {
            if (params[questionId].constructor === Array) {
                params[questionId].push(value);
            } else {
                params[questionId] = [params[questionId], value];
            }
        } else {
            params[questionId] = value;
        }
        return params;
    },

    /**
    *   Prepare comment before submitting form.
    *   This method extract the comment, encapsulate it in a dict and calls the _prepareSubmitAnswer methods
    *   with the new value. At the end, the result looks like :
    *   params = { 'questionId1' : {'comment': commentValue}, 'questionId2' : [multipleAnswer1, {'comment': commentValue}, ...] }
    */
    _prepareSubmitComment: function(params, $parent, questionId, isMatrix) {
        var self = this;
        $parent.find('textarea').each(function () {
            if (this.value) {
                var value = {'comment': this.value};
                if (isMatrix) {
                    params = self._prepareSubmitAnswerMatrix(params, questionId, this.name, value);
                } else {
                    params = self._prepareSubmitAnswer(params, questionId, value);
                }
            }
        });
        return params
    },

    // INIT FIELDS TOOLS
    // -------------------------------------------------------------------------

    /**
    * Initialize datetimepicker in correct format and with constraints
    */
    _initDateTimePicker: function ($dateGroup) {
        var disabledDates = []

        var minDateData = $dateGroup.data('mindate')
        var minDate = minDateData ? this._formatDateTime(minDateData) : moment({ y: 1900 });
        var maxDateData = $dateGroup.data('maxdate')
        var maxDate = maxDateData ? this._formatDateTime(maxDateData) : moment().add(200, "y");

        var datetimepickerFormat = time.getLangDateFormat()
        if ($dateGroup.find('input').data('questionType') === 'datetime') {
            datetimepickerFormat = time.getLangDatetimeFormat()
        } else {
            // Include min and max date in selectable values
            maxDate = moment(maxDate).add(1, "d");
            minDate = moment(minDate).subtract(1, "d");
            disabledDates = [minDate, maxDate]
        }

        $dateGroup.datetimepicker({
            format : datetimepickerFormat,
            minDate: minDate,
            maxDate: maxDate,
            disabledDates: disabledDates,
            useCurrent: false,
            viewDate: moment(new Date()).hours(0).minutes(0).seconds(0).milliseconds(0),
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
        });
        $dateGroup.on('error.datetimepicker', function () {
            return false;
        });
    },

    _formatDateTime: function (datetimeValue){
        return field_utils.format.datetime(moment(datetimeValue), null, {timezone: true});
    },

    // ERRORS TOOLS
    // -------------------------------------------------------------------------

    _scrollToError: function ($target) {
        var scrollLocation = $target.offset().top;
        var navbarHeight = $('.o_main_navbar').height();
        if (navbarHeight != undefined) {
            scrollLocation -= navbarHeight
        }
        $('html, body').animate({
            scrollTop: scrollLocation
        }, 500);
    },

    /**
    * Clean all form errors in order to clean DOM before a new validation
    */
    _resetErrors: function () {
        this.$('.o_survey_question_error').empty().toggleClass("d-none", true);
        this.$('.o_survey_error').toggleClass("d-none", true);
    },

});

return publicWidget.registry.SurveyFormWidget;

});
