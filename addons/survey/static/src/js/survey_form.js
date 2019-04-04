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
        'click button[name="button_submit"]': '_onSubmit',
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
            var $timer = self.$('.o_survey_timer');
            if ($timer.length) {
                this.surveyTimerWidget = new publicWidget.registry.SurveyTimerWidget(this);
                this.surveyTimerWidget.attachTo($timer);
                this.surveyTimerWidget.on('time_up', this, function (ev) {
                    self.$el.find('button[name="button_submit"]').click();
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
        var $target = $(event.currentTarget);
        var submitValue = $target.val();
        this._submitForm({'button_submit': submitValue})
    },

    _submitForm: function (params) {
        var self = this;
        var $form = this.$('form');
        var formData = new FormData($form[0]);

        this.$('div.o_survey_form_date').each(function () {
            self._updateDateForSubmit($(this), formData);
        });
        this._prepareSubmitValues(formData, params);

        this._resetErrors();

        return self._rpc({
            route: '/survey/submit/' + self.options['surveyToken'] + '/' + self.options['answerToken'],
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

    // INIT FIELDS
    // -------------------------------------------------------------------------
    /*
    * Convert the client side date format into server side date format before submit
    */
    _updateDateForSubmit: function (dateGroup, formData) {
        var input = $(dateGroup).find('input');
        var dateValue = input.val();
        var questionType = $(input).closest('.o_survey_form_date').data('questiontype');
        if (dateValue) {
            var momentDate = questionType === 'datetime' ? field_utils.parse.datetime(dateValue, null, {timezone: true}) : field_utils.parse.date(dateValue);
            var newDate = momentDate ? momentDate.toJSON() : '';
            formData.set(input.attr('name'), newDate);
            input.val(newDate);
        }
    },

    // TOOLS
    // -------------------------------------------------------------------------
    _prepareSubmitValues: function (formData, params) {
        var self = this;
        formData.forEach(function(value, key){
            if (value !== -1) {
                // Handles Comment
                if (key.indexOf('_comment') !== -1){
                    key = key.split('_comment')[0];
                    value = {'comment': value};
                }
                // Handles Matrix - Matrix answer_tag are composed like : 'questionId_rowId_colId'
                // and are the only ones with this structure.
                var splitKey = key.split('_');
                if (splitKey.length === 3 && splitKey[2] === value) {
                    params = self._prepareSubmitMatrix(params, splitKey, value);
                }
                // Handles the rest
                else {
                    params = self._prepareSubmitOther(params, key, value);
                }
            }
        });
    },

    /**
    *   Prepare answer before submitting form if question type is matrix.
    *   This method regroups answers by question and by row to make a object like :
    *   params = { 'matrixQuestionId' : { 'rowId1' : [colId1, colId2,...], 'rowId2' : [colId1, colId3, ...] } }
    */
    _prepareSubmitMatrix: function(params, splitKey, value) {
        var key = splitKey[0];
        var rowId = splitKey[1];
        var colId = splitKey[2];
        value = key in params ? params[key] : {};
        if (rowId in value) {
            value[rowId].push(colId);
        } else {
            value[rowId] = [colId];
        }
        params[key] = value;
        return params;
    },

    /**
    *   Prepare answer before submitting form (any kind of answer - except Matrix -).
    *   This method regroups answers by question.
    *   Lonely answer are directly assigned to questionId. Multiple answers are regrouped in an array:
    *   params = { 'questionId1' : lonelyAnswer, 'questionId2' : [multipleAnswer1, multipleAnswer2, ...] }
    */
    _prepareSubmitOther: function(params, key, value) {
        if (key in params) {
            if (params[key].constructor === Array) {
                params[key].push(value);
            } else {
                params[key] = [params[key], value];
            }
        } else {
            params[key] = value;
        }
        return params;
    },

    /**
    * Convert date value in client current timezone (if already answered)
    */
    _formatDateValue: function ($dateGroup) {
        var input = $dateGroup.find('input');
        var dateValue = input.val();
        if (dateValue !== '') {
            var momentDate = field_utils.parse.date(dateValue);
            if ($dateGroup.data('questiontype') === 'datetime') {
                dateValue = field_utils.format.datetime(momentDate, null, {timezone: true});
            } else {
                dateValue = field_utils.format.date(momentDate, null, {timezone: true});
            }
        }
        input.val(dateValue);
        return dateValue
    },

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
        if ($dateGroup.data('questiontype') === 'datetime') {
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
