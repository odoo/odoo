odoo.define('survey.form', function (require) {
'use strict';

var field_utils = require('web.field_utils');
var publicWidget = require('web.public.widget');
var time = require('web.time');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');

var _t = core._t;

publicWidget.registry.SurveyFormWidget = publicWidget.Widget.extend({
    selector: '.o_survey_form',
    events: {
        'change .o_survey_form_choice_item': '_onChangeChoiceItem',
        'click .o_survey_matrix_btn': '_onMatrixBtnClick',
        'click button[type="submit"]': '_onSubmit',
    },
    custom_events: {
        'breadcrumb_click': '_onBreadcrumbClick',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    start: function () {
        var self = this;
        this.fadeInOutDelay = 400;
        return this._super.apply(this, arguments).then(function () {
            self.options = self.$target.find('form').data();
            // Init fields
            if (!self.options.isStartScreen) {
                self._initTimer();
                self._initBreadcrumb();
            }
            self.$('div.o_survey_form_date').each(function () {
                self._initDateTimePicker($(this));
            });
            self._initChoiceItems();
            self._initTextArea();
            self._focusOnFirstInput();
            // Init event listener
            if (!self.options.readonly) {
                $(document).on('keypress', self._onKeyPress.bind(self));
            }
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    // Handlers
    // -------------------------------------------------------------------------

    _onKeyPress: function (event) {
        // If user is answering a textarea, do not handle keyPress
        if (this.$("textarea").is(":focus")) {
            return;
        }

        var self = this;
        var keyCode = event.keyCode;
        var letter = String.fromCharCode(keyCode).toUpperCase();

        // Handle Start / Next / Submit
        if (keyCode === 13) {  // Enter : go Next
            event.preventDefault();
            this._submitForm({});
        } else if (self.options.questionsLayout === 'page_per_question'
                   && letter.match(/[a-z]/i)) {
            var $choiceInput = this.$(`input[data-selection-key=${letter}]`);
            if ($choiceInput.length === 1) {
                if ($choiceInput.attr('type') === 'radio') {
                    $choiceInput.prop("checked", true).trigger('change');
                } else {
                    $choiceInput.prop("checked", !$choiceInput.prop("checked")).trigger('change');
                }
                // Avoid selection key to be typed into the textbox if 'other' is selected by key
                event.preventDefault();
            }
        }
    },

    /**
    * Checks, if the 'other' choice is checked. Applies only if the comment count as answer.
    *   If not checked : Clear the comment textarea and disable it
    *   If checked : enable the comment textarea and focus on it
    *
    * @private
    * @param {Event} event
    */
    _onChangeChoiceItem: function (event) {
        var $target = $(event.currentTarget);
        var $choiceItemGroup = $target.closest('.o_survey_form_choice');
        var $otherItem = $choiceItemGroup.find('.o_survey_js_form_other_comment');
        var $commentInput = $choiceItemGroup.find('textarea[type="text"]');

        if ($otherItem.prop('checked') || $commentInput.hasClass('o_survey_comment')) {
            $commentInput.enable();
            if ($otherItem.prop('checked')) {
                $commentInput.focus();
            }
        } else {
            $commentInput.val('');
            $commentInput.enable(false);
        }

        var $matrixBtn = $target.closest('.o_survey_matrix_btn');
        if ($target.attr('type') === 'radio') {
            if ($matrixBtn.length > 0) {
                $matrixBtn.closest('tr').find('td').removeClass('o_survey_selected');
                $matrixBtn.addClass('o_survey_selected');
            } else {
                $choiceItemGroup.find('label').removeClass('o_survey_selected');
                $target.closest('label').addClass('o_survey_selected');
            }
        } else {  // $target.attr('type') === 'checkbox'
            if ($matrixBtn.length > 0) {
                $matrixBtn.toggleClass('o_survey_selected', !$matrixBtn.hasClass('o_survey_selected'));
            } else {
                var $label = $target.closest('label');
                $label.toggleClass('o_survey_selected', !$label.hasClass('o_survey_selected'));
            }
        }
    },

    _onMatrixBtnClick: function (event) {
        if (!this.options.readonly) {
            var $target = $(event.currentTarget);
            var $input = $target.find('input');
            if ($input.attr('type') === 'radio') {
                $input.prop("checked", true).trigger('change');
            } else {
                $input.prop("checked", !$input.prop("checked")).trigger('change');
            }
        }
    },

    _onSubmit: function (event) {
        event.preventDefault();
        var options = {};
        var $target = $(event.currentTarget);
        if ($target.val() === 'previous') {
            options.previousPageId = $target.data('previousPageId');
        } else if ($target.val() === 'finish') {
            options.isFinish = true;
        }
        this._submitForm(options);
    },

    // Custom Events
    // -------------------------------------------------------------------------

    _onBreadcrumbClick: function (event) {
        this._submitForm({'previousPageId': event.data.previousPageId});
    },

    // SUBMIT
    // -------------------------------------------------------------------------

    /**
    * This function will send a json rpc call to the server to
    * - start the survey (if we are on start screen)
    * - submit the answers of the current page
    * Before submitting the answers, they are first validated to avoid latency from the server
    * and allow a fade out/fade in transition of the next question.
    *
    * @param {Array} [options]
    * @param {Integer} [options.previousPageId] navigates to page id
    * @param {Boolean} [options.skipValidation] skips JS validation
    * @param {Boolean} [options.isFinish] fades out breadcrumb and timer
    * @private
    */
    _submitForm: function (options) {
        var self = this;
        var params = {};
        if (options.previousPageId) {
            params.previous_page_id = options.previousPageId;
        }
        var route = "/survey/submit";

        if (this.options.isStartScreen) {
            route = "/survey/begin";
        } else {
            var $form = this.$('form');
            var formData = new FormData($form[0]);

            if (!options.skipValidation) {
                // Validation pre submit
                if (!this._validateForm($form, formData)) {
                    return;
                }
            }

            this._prepareSubmitValues(formData, params);
        }

        var resolveFadeOut;
        var fadeOutPromise = new Promise(function (resolve, reject) {resolveFadeOut = resolve;});

        var selectorsToFadeout = ['.o_survey_form_content'];
        if (options.isFinish) {
            selectorsToFadeout.push('.breadcrumb', '.o_survey_timer');
        }
        self.$(selectorsToFadeout.join(',')).fadeOut(this.fadeInOutDelay, function () {
            resolveFadeOut();
        });
        var submitPromise = self._rpc({
            route: _.str.sprintf('%s/%s/%s', route, self.options.surveyToken, self.options.answerToken),
            params: params,
        });
        Promise.all([fadeOutPromise, submitPromise]).then(function (results) {
            return self._onSubmitDone(results[1], options.isFinish);
        });
    },

    /**
    * Follow the submit and handle the transition from one screen to another
    * Also handle server side validation and displays eventual error messages.
    */
    _onSubmitDone: function (result, isFinish) {
        var self = this;

        if (result && !result.error) {
            this.$(".o_survey_form_content").empty();
            this.$(".o_survey_form_content").html(result);
            this.$('div.o_survey_form_date').each(function () {
                self._initDateTimePicker($(this));
            });
            if (this.options.isStartScreen) {
                this._initTimer();
                this.options.isStartScreen = false;
            }
            if (isFinish) {
                this._initResultWidget();
                if (this.surveyBreadcrumbWidget) {
                    this.$('.o_survey_breadcrumb_container').addClass('d-none');
                    this.surveyBreadcrumbWidget.destroy();
                }
                if (this.surveyTimerWidget) {
                    this.surveyTimerWidget.destroy();
                }
            } else {
                this._updateBreadcrumb();
            }
            self._initChoiceItems();
            self._initTextArea();
            this.$('.o_survey_form_content').fadeIn(this.fadeInOutDelay);
            $("html, body").animate({ scrollTop: 0 }, this.fadeInOutDelay);
            self._focusOnFirstInput();
        }
        else if (result && result.fields && result.error === 'validation') {
            this.$('.o_survey_form_content').fadeIn(0);
            this._showErrors(result.fields);
        } else {
            var $errorTarget = this.$('.o_survey_error');
            $errorTarget.removeClass("d-none");
            this._scrollToError($errorTarget);
        }
    },

    // VALIDATION TOOLS
    // -------------------------------------------------------------------------
    /**
    * Validation is done in frontend before submit to avoid latency from the server.
    * If the validation is incorrect, the errors are displayed before submitting and
    * fade in / out of submit is avoided.
    *
    * Each question type gets its own validation process.
    *
    * There is a special use case for the 'required' questions, where we use the constraint
    * error message that comes from the question configuration ('constr_error_msg' field).
    *
    * @private
    */
    _validateForm: function ($form, formData) {
        var self = this;
        var errors = {};
        var validationEmailMsg = _t("This answer must be an email address.");
        var validationDateMsg = _t("This is not a date");

        this._resetErrors();

        var data = {};
        formData.forEach(function (value, key) {
            data[key] = value;
        });

        $form.find('[data-question-type]').each(function () {
            var $input = $(this);
            var $questionWrapper = $input.closest(".js_question-wrapper");
            var constrErrorMsg = $questionWrapper.data('constrErrorMsg');
            var validationErrorMsg = $questionWrapper.data('validationErrorMsg');
            var questionId = $questionWrapper.attr('id');
            var questionRequired = $questionWrapper.data('required');
            switch ($input.data('questionType')) {
                case 'char_box':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    } else if ($input.val() && $input.attr('type') === 'email' && !self._validateEmail($input.val())) {
                        errors[questionId] = validationEmailMsg;
                    } else {
                        var lengthMin = $input.data('validationLengthMin');
                        var lengthMax = $input.data('validationLengthMax');
                        var length = $input.val().length;
                        if (lengthMin && (lengthMin > length || length > lengthMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case 'numerical_box':
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else {
                        var floatMin = $input.data('validationFloatMin');
                        var floatMax = $input.data('validationFloatMax');
                        var value = parseFloat($input.val());
                        if (floatMin && (floatMin > value || value > floatMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case 'date':
                case 'datetime':
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else if (data[questionId]) {
                        var momentDate = moment($input.val());
                        if (!momentDate.isValid()) {
                            errors[questionId] = validationDateMsg;
                        } else {
                            var $dateDiv = $questionWrapper.find('.o_survey_form_date');
                            var maxDate = $dateDiv.data('maxdate');
                            var minDate = $dateDiv.data('mindate');
                            if ((maxDate && momentDate.isAfter(moment(maxDate)))
                                    || (minDate && momentDate.isBefore(moment(minDate)))) {
                                errors[questionId] = validationErrorMsg;
                            }
                        }
                    }
                    break;
                case 'simple_choice_radio':
                case 'multiple_choice':
                    if (questionRequired) {
                        var $textarea = $questionWrapper.find('textarea');
                        if (!data[questionId]) {
                            errors[questionId] = constrErrorMsg;
                        } else if (data[questionId] === '-1' && !$textarea.val()) {
                            // if other has been checked and value is null
                            errors[questionId] = constrErrorMsg;
                        }
                    }
                    break;
                case 'matrix':
                    if (questionRequired) {
                        var subQuestionsIds = $questionWrapper.find('table').data('subQuestions');
                        subQuestionsIds.forEach(function (id) {
                            if (!((questionId + '_' + id) in data)) {
                                errors[questionId] = constrErrorMsg;
                            }
                        });
                    }
                    break;
            }
        });
        if (_.keys(errors).length > 0) {
            this._showErrors(errors);
            return false;
        }
        return true;
    },

    /**
    * Check if the email has an '@', a left part and a right part
    * @private
    */
    _validateEmail: function (email) {
        var emailParts = email.split('@');
        return emailParts.length === 2 && emailParts[0] && emailParts[1];
    },

    // PREPARE SUBMIT TOOLS
    // -------------------------------------------------------------------------
    /**
    * For each type of question, extract the answer from inputs or textarea (comment or answer)
    *
    *
    * @private
    * @param {Event} event
    */
    _prepareSubmitValues: function (formData, params) {
        var self = this;
        formData.forEach(function (value, key) {
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
                case 'text_box':
                case 'char_box':
                case 'numerical_box':
                    params[this.name] = this.value;
                    break;
                case 'date':
                    params = self._prepareSubmitDates(params, this.name, this.value, false);
                    break;
                case 'datetime':
                    params = self._prepareSubmitDates(params, this.name, this.value, true);
                    break;
                case 'simple_choice_radio':
                case 'multiple_choice':
                    params = self._prepareSubmitChoices(params, $(this), $(this).data('name'));
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
    _prepareSubmitDates: function (params, questionId, value, isDateTime) {
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
    _prepareSubmitChoices: function (params, $parent, questionId) {
        var self = this;
        $parent.find('input:checked').each(function () {
            if (this.value !== '-1') {
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
    _prepareSubmitAnswersMatrix: function (params, $matrixTable) {
        var self = this;
        $matrixTable.find('input:checked').each(function () {
            params = self._prepareSubmitAnswerMatrix(params, $matrixTable.data('name'), $(this).data('rowId'), this.value);
        });
        params = self._prepareSubmitComment(params, $matrixTable.closest('.js_question-wrapper'), $matrixTable.data('name'), true);
        return params;
    },

    /**
    *   Prepare answer before submitting form if question type is matrix.
    *   This method regroups answers by question and by row to make an object like :
    *   params = { 'matrixQuestionId' : { 'rowId1' : [colId1, colId2,...], 'rowId2' : [colId1, colId3, ...] } }
    */
    _prepareSubmitAnswerMatrix: function (params, questionId, rowId, colId, isComment) {
        var value = questionId in params ? params[questionId] : {};
        if (isComment) {
            value['comment'] = colId;
        } else {
            if (rowId in value) {
                value[rowId].push(colId);
            } else {
                value[rowId] = [colId];
            }
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
    _prepareSubmitAnswer: function (params, questionId, value) {
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
    _prepareSubmitComment: function (params, $parent, questionId, isMatrix) {
        var self = this;
        $parent.find('textarea').each(function () {
            if (this.value) {
                var value = {'comment': this.value};
                if (isMatrix) {
                    params = self._prepareSubmitAnswerMatrix(params, questionId, this.name, this.value, true);
                } else {
                    params = self._prepareSubmitAnswer(params, questionId, value);
                }
            }
        });
        return params;
    },

    // INIT FIELDS TOOLS
    // -------------------------------------------------------------------------

   /**
    * Will allow the textarea to resize on carriage return instead of showing scrollbar.
    */
    _initTextArea: function () {
        this.$('textarea').each(function () {
            dom.autoresize($(this));
        });
    },

    _initChoiceItems: function () {
        this.$("input[type='radio'],input[type='checkbox']").each(function () {
            var matrixBtn = $(this).parents('.o_survey_matrix_btn');
            if ($(this).prop("checked")) {
                var $target = matrixBtn.length > 0 ? matrixBtn : $(this).closest('label');
                $target.addClass('o_survey_selected');
            }
        });
    },

    /**
     * Will initialize the breadcrumb widget that handles navigation to a previously filled in page.
     *
     * @private
     */
    _initBreadcrumb: function () {
        var $breadcrumb = this.$('.o_survey_breadcrumb_container');
        var pageId = this.$('input[name=page_id]').val();
        if ($breadcrumb.length) {
            this.surveyBreadcrumbWidget = new publicWidget.registry.SurveyBreadcrumbWidget(this, {
                'canGoBack': $breadcrumb.data('canGoBack'),
                'currentPageId': pageId ? parseInt(pageId) : 0,
                'pages': $breadcrumb.data('pages'),
            });
            this.surveyBreadcrumbWidget.appendTo($breadcrumb);
            $breadcrumb.removeClass('d-none');  // hidden by default to avoid having ghost div in start screen
        }
    },

    /**
     * Called after survey submit to update the breadcrumb to the right page.
     */
    _updateBreadcrumb: function () {
        if (this.surveyBreadcrumbWidget) {
            var pageId = this.$('input[name=page_id]').val();
            this.surveyBreadcrumbWidget.updateBreadcrumb(parseInt(pageId));
        } else {
            this._initBreadcrumb();
        }
    },

    _initTimer: function () {
        var self = this;
        var $timer = this.$('.o_survey_timer');
        if ($timer.length) {
            var timeLimitMinutes = this.options.timeLimitMinutes;
            var timer = this.options.timer;
            this.surveyTimerWidget = new publicWidget.registry.SurveyTimerWidget(this, {
                'timer': timer,
                'timeLimitMinutes': timeLimitMinutes
            });
            this.surveyTimerWidget.attachTo($timer);
            this.surveyTimerWidget.on('time_up', this, function (ev) {
                self._submitForm({
                    'skipValidation': true,
                    'isFinish': true
                });
            });
            $timer.removeClass('d-none');
        }
    },

    /**
    * Initialize datetimepicker in correct format and with constraints
    */
    _initDateTimePicker: function ($dateGroup) {
        var disabledDates = []
        var minDateData = $dateGroup.data('mindate')
        var maxDateData = $dateGroup.data('maxdate')

        var datetimepickerFormat = time.getLangDateFormat();
        if ($dateGroup.find('input').data('questionType') === 'datetime') {
            datetimepickerFormat = time.getLangDatetimeFormat();
        } else {
            // Include min and max date in selectable values
            maxDate = moment(maxDate).add(1, "d");
            minDate = moment(minDate).subtract(1, "d");
            disabledDates = [minDate, maxDate];
        }

        var minDate = minDateData
                        ? this._formatDateTime(minDateData, datetimepickerFormat)
                        : moment({ y: 1900 });
        var maxDate = maxDateData
                        ? this._formatDateTime(maxDateData, datetimepickerFormat)
                        : moment().add(200, "y");

        $dateGroup.datetimepicker({
            format : datetimepickerFormat,
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
        });
        $dateGroup.on('error.datetimepicker', function (err) {
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
    },

    _formatDateTime: function (datetimeValue, format){
        return moment(field_utils.format.datetime(moment(datetimeValue), null, {timezone: true}), format);
    },

    _initResultWidget: function () {
        var $result = this.$('.o_survey_result');
        if ($result.length) {
            this.surveyResultWidget = new publicWidget.registry.SurveyResultWidget(this);
            this.surveyResultWidget.attachTo($result);
            $result.fadeIn(this.fadeInOutDelay);
        }
    },

   /**
    * Will automatically focus on the first input to allow the user to complete directly the survey,
    * without having to manually get the focus (only if the input has the right type - can write something inside -)
    */
    _focusOnFirstInput: function () {
        var $firstTextInput = this.$('.js_question-wrapper').first()  // Take first question
                              .find("input[type='text'],input[type='number'],textarea")  // get 'text' inputs
                              .filter('.form-control')  // needed for the auto-resize
                              .not('.o_survey_comment');  // remove inputs for comments that does not count as answers
        if ($firstTextInput.length > 0) {
            $firstTextInput.focus();
        }
    },

    // ERRORS TOOLS
    // -------------------------------------------------------------------------

    _showErrors: function (errors) {
        var self = this;
        var errorKeys = _.keys(errors);
        _.each(errorKeys, function (key) {
            self.$("#" + key + '>.o_survey_question_error').append($('<p>', {text: errors[key]})).addClass("slide_in");
            if (errorKeys[0] === key) {
                self._scrollToError(self.$('.js_question-wrapper#' + key));
            }
        });
    },

    _scrollToError: function ($target) {
        var scrollLocation = $target.offset().top;
        var navbarHeight = $('.o_main_navbar').height();
        if (navbarHeight) {
            // In overflow auto, scrollLocation of target can be negative if target is out of screen (up side)
            scrollLocation = scrollLocation >= 0 ? scrollLocation - navbarHeight : scrollLocation + navbarHeight;
        }
        var scrollinside = $("#wrapwrap").scrollTop();
        $('#wrapwrap').animate({
            scrollTop: scrollinside + scrollLocation
        }, 500);
    },

    /**
    * Clean all form errors in order to clean DOM before a new validation
    */
    _resetErrors: function () {
        this.$('.o_survey_question_error').empty().removeClass('slide_in');
        this.$('.o_survey_error').addClass('d-none');
    },

});

return publicWidget.registry.SurveyFormWidget;

});
