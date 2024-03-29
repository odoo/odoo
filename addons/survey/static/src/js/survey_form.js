/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { cookie } from "@web/core/browser/cookie";
import { utils as uiUtils } from "@web/core/ui/ui_service";

import SurveyPreloadImageMixin from "@survey/js/survey_preload_image_mixin";
import { SurveyImageZoomer } from "@survey/js/survey_image_zoomer";
import {
    deserializeDate,
    deserializeDateTime,
    parseDateTime,
    parseDate,
    serializeDateTime,
    serializeDate,
} from "@web/core/l10n/dates";
import { resizeTextArea } from "@web/core/utils/autoresize";
const { DateTime } = luxon;

var isMac = navigator.platform.toUpperCase().includes('MAC');

publicWidget.registry.SurveyFormWidget = publicWidget.Widget.extend(SurveyPreloadImageMixin, {
    selector: '.o_survey_form',
    events: {
        'change .o_survey_form_choice_item': '_onChangeChoiceItem',
        'click .o_survey_matrix_btn': '_onMatrixBtnClick',
        'click input[type="radio"]': '_onRadioChoiceClick',
        'click button[type="submit"]': '_onSubmit',
        'click .o_survey_choice_img img': '_onChoiceImgClick',
        'focusin .form-control': '_updateEnterButtonText',
        'focusout .form-control': '_updateEnterButtonText'
    },
    custom_events: {
        'breadcrumb_click': '_onBreadcrumbClick',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
    * @override
    */
    start: function () {
        var self = this;
        this.fadeInOutDelay = 400;
        return this._super.apply(this, arguments).then(function () {
            self.options = self.$('form').data();
            self.readonly = self.options.readonly;
            self.selectedAnswers = self.options.selectedAnswers;
            self.imgZoomer = false;

            // Add Survey cookie to retrieve the survey if you quit the page and restart the survey.
            if (!cookie.get('survey_' + self.options.surveyToken)) {
                cookie.set('survey_' + self.options.surveyToken, self.options.answerToken, 60 * 60 * 24, 'optional');
            }

            // Init fields
            if (!self.options.isStartScreen && !self.readonly) {
                self._initTimer();
                self._initBreadcrumb();
            }
            self._initChoiceItems();
            self._initTextArea();
            self._focusOnFirstInput();
            // Init event listener
            if (!self.readonly) {
                self.documentKeydownListener = self._onKeyDown.bind(self);
                $(document).on('keydown', self.documentKeydownListener);
            }
            if (self.options.sessionInProgress &&
                (self.options.isStartScreen || self.options.hasAnswered || self.options.isPageDescription)) {
                self.preventEnterSubmit = true;
            }
            self._initSessionManagement();

            // Needs global selector as progress/navigation are not within the survey form, but need
            //to be updated at the same time
            self.$surveyProgress = $('.o_survey_progress_wrapper');
            self.$surveyNavigation = $('.o_survey_navigation_wrapper');
            self.$surveyNavigation.find('.o_survey_navigation_submit').on('click', self._onSubmit.bind(self));

            self.$('button[type="submit"]').removeClass('disabled');
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handle keyboard navigation:
     * - 'enter' or 'arrow-right' => submit form
     * - 'arrow-left' => submit form (but go back backwards)
     * - other alphabetical character ('a', 'b', ...)
     *   Select the related option in the form (if available)
     *
     * @param {Event} event
     */
    _onKeyDown: function (event) {
        var self = this;

        if (['one_page', 'page_per_section'].includes(self.options.questionsLayout) && !self.options.isStartScreen) {
            if (this.$("input").is(":focus") && event.key === "Enter") {
                event.preventDefault();
            }
            if (!(event.ctrlKey || event.metaKey) || event.key !== "Enter") {
                return;
            }
        }

        // If user is answering a text input, do not handle keydown
        // CTRL+enter will force submission (meta key for Mac)
        if ((this.$("textarea").is(":focus") || this.$('input').is(':focus')) &&
            (!(event.ctrlKey || event.metaKey) || event.key !== "Enter")) {
            return;
        }
        // If in session mode and question already answered, do not handle keydown
        if (this.$('fieldset[disabled="disabled"]').length !== 0) {
            return;
        }
        // Disable all navigation keys when zoom modal is open, except the ESC.
        if ((this.imgZoomer && !this.imgZoomer.isDestroyed()) && event.key !== "Escape") {
            return;
        }

        var letter = event.key.toUpperCase();

        // Handle Start / Next / Submit
        if (event.key === "Enter" || event.key === "ArrowRight") {  // Enter or arrow-right: go Next
            event.preventDefault();
            if (!this.preventEnterSubmit) {
                this._submitForm({
                    isFinish: this.el.querySelectorAll('button[value="finish"]').length !== 0,
                    nextSkipped: this.el.querySelectorAll('button[value="next_skipped"]').length !== 0 ? event.key === "Enter" : false,
                });
            }
        } else if (event.key === "ArrowLeft") {  // arrow-left: previous (if available)
            // It's easier to actually click on the button (if in the DOM) as it contains necessary
            // data that are used in the event handler.
            // Again, global selector necessary since the navigation is outside of the form.
            $('.o_survey_navigation_submit[value="previous"]').click();
        } else if (self.options.questionsLayout === 'page_per_question'
                   && letter.match(/[a-z]/i)) {
            var $choiceInput = this.$(`input[data-selection-key=${letter}]`);
            if ($choiceInput.length === 1) {
                $choiceInput.prop("checked", !$choiceInput.prop("checked")).trigger('change');

                // Avoid selection key to be typed into the textbox if 'other' is selected by key
                event.preventDefault();
            }
        }
    },

    /**
     * Handle visibility of comment area and conditional questions
     * The form (page) is then automatically submitted if:
     * - Survey is configured with one page per question and participants are allowed to go back,
     * - It is not the last question of the survey,
     * - The question is not waiting for a comment (with "Other" answer),
     *
     * @param event
     */
    _onChangeChoiceItem: function (event) {
        const $target = $(event.currentTarget);
        const $choiceItemGroup = $target.closest('.o_survey_form_choice');

        this._applyCommentAreaVisibility($choiceItemGroup);
        const isQuestionComplete = this._checkConditionalQuestionsConfiguration($target, $choiceItemGroup);
        if (isQuestionComplete && this.options.usersCanGoBack) {
            const isLastQuestion = this.$('button[value="finish"]').length !== 0;
            if (!isLastQuestion) {
                const questionHasComment = $target.hasClass('o_survey_js_form_other_comment') || $target
                    .closest('.o_survey_form_choice')
                    .find('.o_survey_comment').length !== 0;
                if (!questionHasComment) {
                    this._submitForm({'nextSkipped': $choiceItemGroup.data('isSkippedQuestion')});
                }
            }
        }
    },

    /**
     * Called when an image on an answer in multi-answers question is clicked.
     * Starts a widget opening a dialog to display the now zoomable image.
     * this.imgZoomer is the zoomer widget linked to the survey form, if any.
     *
     * @private
     * @param {Event} ev
     */
    _onChoiceImgClick: function (ev) {
        ev.preventDefault();
        this.imgZoomer = new SurveyImageZoomer({
            sourceImage: $(ev.currentTarget).attr('src')
        });
        this.imgZoomer.appendTo(document.body);
    },

    /**
     * Invert the related input's "checked" property.
     * This will tick or untick the option (based on the previous state).
     *
     * @param {MouseEvent} event
     * @returns
     */
    _onMatrixBtnClick: function (event) {
        if (this.readonly) {
            return;
        }

        var $target = $(event.currentTarget);
        var $input = $target.find('input');
        $input.prop("checked", !$input.prop("checked")).trigger('change');
    },

    /**
     * Base browser behavior when clicking on a radio input is to leave the radio checked if it was
     * already checked before.
     * Here for survey we want to be able to un-tick the choice.
     *
     * e.g: You select an option but on second thoughts you're unsure it's the right answer, you
     * want to be able to remove your answer.
     *
     * To do so, we use an alternate class "o_survey_form_choice_item_selected" that is added when
     * the option is ticked and removed when the option is unticked.
     *
     * - When it's ticked, we simply add the class (the browser will set the "checked" property
     *   to true).
     * - When it's unticked, we manually set the "checked" property of the element to "false".
     *   We also trigger the 'change' event to go into '_onChangeChoiceItem'.
     *
     * @param {MouseEvent} event
     */
    _onRadioChoiceClick: function (event) {
        var $target = $(event.currentTarget);
        if ($target.hasClass("o_survey_form_choice_item_selected")) {
            $target.prop("checked", false).removeClass("o_survey_form_choice_item_selected");
            $target.trigger('change');
        } else {
            this.$(`input:radio[name="${$target.prop("name")}"].o_survey_form_choice_item_selected`)
                .removeClass("o_survey_form_choice_item_selected");
            $target.addClass("o_survey_form_choice_item_selected");
        }
    },

    _onSubmit: function (event) {
        event.preventDefault();
        const options = {};
        const target = event.currentTarget;
        if (target.value === 'previous') {
            options.previousPageId = parseInt(target.dataset['previousPageId']);
        } else if (target.value === 'next_skipped') {
            options.nextSkipped = true;
        } else if (target.value === 'finish') {
            options.isFinish = true;
        }
        this._submitForm(options);
    },

    // Custom Events
    // -------------------------------------------------------------------------

    /**
     * Changes the tooltip according to the type of the field.
     * @param {Event} event
     */
    _updateEnterButtonText: function (event) {
        const $target = event.target;
        const isTextbox = event.type === "focusin" && $target.tagName.toLowerCase() === 'textarea';
        let text = _t("or press Enter");
        if (['one_page', 'page_per_section'].includes(this.options.questionsLayout) || isTextbox) {
            text = isMac ? _t("or press ⌘+Enter") : _t("or press CTRL+Enter");
        }
        $('#enter-tooltip').text(text);
    },

    _onBreadcrumbClick: function (event) {
        this._submitForm({'previousPageId': event.data.previousPageId});
    },

    /**
     * We listen to 'next_question' and 'end_session' events to load the next
     * page of the survey automatically, based on the host pacing.
     *
     * If the trigger is 'next_question', we handle some extra computation to find
     * a suitable "fadeInOutDelay" based on the delay between the time of the question
     * change by the host and the time of reception of the event.
     * This will allow us to account for a little bit of server lag (up to 1 second)
     * while giving everyone a fair experience on the quiz.
     *
     * e.g 1:
     * - The host switches the question
     * - We receive the event 200 ms later due to server lag
     * - -> The fadeInOutDelay will be 400 ms (200ms delay + 400ms * 2 fade in fade out)
     *
     * e.g 2:
     * - The host switches the question
     * - We receive the event 600 ms later due to bigger server lag
     * - -> The fadeInOutDelay will be 200ms (600ms delay + 200ms * 2 fade in fade out)
     *
     * @private
     * @param {CustomEvent} ev
     * @param {Array[]} [ev.detail] notifications structured as specified by the bus feature
     */
    _onNotification: function ({ detail: notifications }) {
        var nextPageEvent = false;
        if (notifications && notifications.length !== 0) {
            notifications.forEach(function (notification) {
                if (notification.type === 'next_question' ||
                    notification.type === 'end_session') {
                    nextPageEvent = notification;
                }
            });
        }

        if (this.options.isStartScreen && nextPageEvent.type === 'end_session') {
            // can happen when triggering the same survey session multiple times
            // we received an "old" end_session event that needs to be ignored
            return;
        }

        if (nextPageEvent) {
            if (nextPageEvent.type === 'next_question') {
                var serverDelayMS =
                   (DateTime.now().toSeconds() - nextPageEvent.payload.question_start) * 1000;
                if (serverDelayMS < 0) {
                    serverDelayMS = 0;
                } else if (serverDelayMS > 1000) {
                    serverDelayMS = 1000;
                }
                this.fadeInOutDelay = (1000 - serverDelayMS) / 2;
            } else {
                this.fadeInOutDelay = 400;
            }

            this.$('.o_survey_main_title:visible').fadeOut(400);

            this.preventEnterSubmit = false;
            this.readonly = false;
            this._nextScreen(
                this.rpc(
                    `/survey/next_question/${this.options.surveyToken}/${this.options.answerToken}`
                ), {
                    initTimer: true,
                    isFinish: nextPageEvent.type === 'end_session'
                }
            );
        }
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
    * @param {Boolean} [options.initTime] will force the re-init of the timer after next
    *   screen transition
    * @param {Boolean} [options.isFinish] fades out breadcrumb and timer
    * @private
    */
    _submitForm: async function (options) {
        var params = {};
        if (options.previousPageId) {
            params.previous_page_id = options.previousPageId;
        }
        if (options.nextSkipped) {
            params.next_skipped_page_or_question = true;
        }
        var route = "/survey/submit";

        if (this.options.isStartScreen) {
            route = "/survey/begin";
            // Hide survey title in 'page_per_question' layout: it takes too much space
            if (this.options.questionsLayout === 'page_per_question') {
                this.$('.o_survey_main_title').fadeOut(400);
            }
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

        // prevent user from submitting more times using enter key
        this.preventEnterSubmit = true;

        if (this.options.sessionInProgress) {
            // reset the fadeInOutDelay when attendee is submitting form
            this.fadeInOutDelay = 400;
            // prevent user from clicking on matrix options when form is submitted
            this.readonly = true;
        }

        const submitPromise = this.rpc(
            `${route}/${this.options.surveyToken}/${this.options.answerToken}`,
            params
        );

        if (!this.options.isStartScreen && this.options.scoringType == 'scoring_with_answers_after_page') {
            const [correctAnswers] = await submitPromise;
            if (Object.keys(correctAnswers).length && document.querySelector('.js_question-wrapper')) {
                this._showCorrectAnswers(correctAnswers, submitPromise, options);
                return;
            }
        }
        this._nextScreen(submitPromise, options);
    },

    /**
     * Will fade out / fade in the next screen based on passed promise and options.
     *
     * @param {Promise} nextScreenPromise
     * @param {Object} options see '_submitForm' for details
     */
    _nextScreen: async function (nextScreenPromise, options) {
        var resolveFadeOut;
        var fadeOutPromise = new Promise(function (resolve, reject) {resolveFadeOut = resolve;});

        var selectorsToFadeout = ['.o_survey_form_content'];
        if (options.isFinish && !this.nextScreenResult?.has_skipped_questions) {
            selectorsToFadeout.push('.breadcrumb', '.o_survey_timer');
            cookie.delete('survey_' + this.options.surveyToken);
        }
        this.$(selectorsToFadeout.join(',')).fadeOut(this.fadeInOutDelay, function () {
            resolveFadeOut();
        });
        // Background management - Fade in / out on each transition
        if (this.options.refreshBackground) {
            $('div.o_survey_background').addClass('o_survey_background_transition');
        }

        const nextScreenWithBackgroundPromise = (async () => {
            const [,result] = await nextScreenPromise;
            this.nextScreenResult = result;
            // once we have the next question, wait for the preload of the background
            if (this.options.refreshBackground && result.background_image_url) {
                return this._preloadBackground(result.background_image_url);
            } else {
                return Promise.resolve();
            }
        })();

        // Wait for the fade out and the preload of the next background. The next question have already been fetched.
        await Promise.all([fadeOutPromise, nextScreenWithBackgroundPromise]);
        return this._onNextScreenDone(options);
    },

    /**
     * Handle server side validation and display eventual error messages.
     *
     * @param {Object} options see '_submitForm' for details
     */
    _onNextScreenDone: function (options) {
        var self = this;
        var result = this.nextScreenResult;

        if ((!(options && options.isFinish) || result.has_skipped_questions)
            && !this.options.sessionInProgress) {
            this.preventEnterSubmit = false;
        }

        if (result && !result.error) {
            this.$(".o_survey_form_content").empty();
            this.$(".o_survey_form_content").html(result.survey_content);

            if (result.survey_progress && this.$surveyProgress.length !== 0) {
                this.$surveyProgress.html(result.survey_progress);
            } else if (options.isFinish && this.$surveyProgress.length !== 0) {
                this.$surveyProgress.remove();
            }

            if (result.survey_navigation && this.$surveyNavigation.length !== 0) {
                this.$surveyNavigation.html(result.survey_navigation);
                this.$surveyNavigation.find('.o_survey_navigation_submit').on('click', self._onSubmit.bind(self));
            }

            // Hide timer if end screen (if page_per_question in case of conditional questions)
            if (self.options.questionsLayout === 'page_per_question' && this.$('.o_survey_finished').length > 0) {
                options.isFinish = true;
            }

            // Start datetime pickers
            self.trigger_up("widgets_start_request", { $target: this.$el.find('.o_survey_form_date') });
            if (this.options.isStartScreen || (options && options.initTimer)) {
                this._initTimer();
                this.options.isStartScreen = false;
            } else {
                if (this.options.sessionInProgress && this.surveyTimerWidget) {
                    this.surveyTimerWidget.destroy();
                }
            }
            if (options && options.isFinish && !result.has_skipped_questions) {
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

            if (this.options.sessionInProgress && this.$('.o_survey_form_content_data').data('isPageDescription')) {
                // prevent enter submit if we're on a page description (there is nothing to submit)
                this.preventEnterSubmit = true;
            }
            // Background management - reset background overlay opacity to 0.7 to discover next background.
            if (this.options.refreshBackground) {
                $('div.o_survey_background').css("background-image", "url(" + result.background_image_url + ")");
                $('div.o_survey_background').removeClass('o_survey_background_transition');
            }
            this.$('.o_survey_form_content').fadeIn(this.fadeInOutDelay);
            $("html, body").animate({ scrollTop: 0 }, this.fadeInOutDelay);

            this.$('button[type="submit"]').removeClass('disabled');

            this._scrollToFirstError();
            self._focusOnFirstInput();
        } else if (result && result.fields && result.error === 'validation') {
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

        var inactiveQuestionIds = this.options.sessionInProgress ? [] : this._getInactiveConditionalQuestionIds();

        $form.find('[data-question-type]').each(function () {
            var $input = $(this);
            var $questionWrapper = $input.closest(".js_question-wrapper");
            var questionId = $questionWrapper.attr('id');

            // If question is inactive, skip validation.
            if (inactiveQuestionIds.includes(parseInt(questionId))) {
                return;
            }

            var questionRequired = $questionWrapper.data('required');
            var constrErrorMsg = $questionWrapper.data('constrErrorMsg');
            var validationErrorMsg = $questionWrapper.data('validationErrorMsg');
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
                case 'text_box':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
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
                        const [parse, deserialize] =
                            $input.data("questionType") === "date"
                                ? [parseDate, deserializeDate]
                                : [parseDateTime, deserializeDateTime];
                        const date = parse($input.val());
                        if (!date || !date.isValid) {
                            errors[questionId] = validationDateMsg;
                        } else {
                            const maxDate = deserialize($input.data('max-date'));
                            const minDate = deserialize($input.data('min-date'));
                            if (
                                (maxDate.isValid && date > maxDate) ||
                                (minDate.isValid && date < minDate)
                            ) {
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
                        const subQuestionsIds = $questionWrapper.find('table').data('subQuestions');
                        // Highlight unanswered rows' header
                        const questionBodySelector = `div[id="${questionId}"] > .o_survey_question_matrix > tbody`;
                        subQuestionsIds.forEach((subQuestionId) => {
                            if (!(`${questionId}_${subQuestionId}` in data)) {
                                errors[questionId] = constrErrorMsg;
                                self.el.querySelector(`${questionBodySelector} > tr[id="${subQuestionId}"] > th`).classList.add('bg-danger');
                            }
                        });
                    }
                    break;
            }
        });
        if (Object.keys(errors).length > 0) {
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
                case 'datetime':{
                    const [parse, serialize] =
                        $(this).data("questionType") === "date"
                            ? [parseDate, serializeDate]
                            : [parseDateTime, serializeDateTime];
                    const date = parse(this.value);
                    params[this.name] = date ? serialize(date) : "";
                    break;
                }
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
            resizeTextArea(this);
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

    /**
     * Will handle bus specific behavior for survey 'sessions'
     *
     * @private
     */
    _initSessionManagement: function () {
        var self = this;
        if (this.options.surveyToken && this.options.sessionInProgress) {
            this.call('bus_service', 'addChannel', this.options.surveyToken);

            if (!this._checkisOnMainTab()) {
                this.shouldReloadMasterTab = true;
                this.masterTabCheckInterval = setInterval(function () {
                     if (self._checkisOnMainTab()) {
                        clearInterval(self.masterTabCheckInterval);
                     }
                }, 2000);
            }

            this.call('bus_service', 'addEventListener', 'notification', this._onNotification.bind(this));
        }
    },

    _initTimer: function () {
        if (this.surveyTimerWidget) {
            this.surveyTimerWidget.destroy();
        }

        var self = this;
        var $timerData = this.$('.o_survey_form_content_data');
        var questionTimeLimitReached = $timerData.data('questionTimeLimitReached');
        var timeLimitMinutes = $timerData.data('timeLimitMinutes');
        var hasAnswered = $timerData.data('hasAnswered');
        const serverTime = $timerData.data('serverTime');

        if (!questionTimeLimitReached && !hasAnswered && timeLimitMinutes) {
            var timer = $timerData.data('timer');
            var $timer = $('<span>', {
                class: 'o_survey_timer'
            });
            this.$('.o_survey_timer_container').append($timer);
            this.surveyTimerWidget = new publicWidget.registry.SurveyTimerWidget(this, {
                'serverTime': serverTime,
                'timer': timer,
                'timeLimitMinutes': timeLimitMinutes
            });
            this.surveyTimerWidget.attachTo($timer);
            this.surveyTimerWidget.on('time_up', this, function (ev) {
                self._submitForm({
                    'skipValidation': true,
                    'isFinish': !this.options.sessionInProgress
                });
            });
        }
    },

    _initResultWidget: function () {
        var $result = this.$('.o_survey_result');
        if ($result.length) {
            this.surveyResultWidget = new publicWidget.registry.SurveyResultWidget(this);
            this.surveyResultWidget.attachTo($result);
            $result.fadeIn(this.fadeInOutDelay);
        }
    },

    // OTHER TOOLS
    // -------------------------------------------------------------------------

    /**
    * Checks, if the 'other' choice is checked. Applies only if the comment count as answer.
    *   If not checked : Clear the comment textarea, hide and disable it
    *   If checked : enable the comment textarea, show and focus on it
    *
    * @param {JQuery<HTMLElement>} $choiceItemGroup
    */
    _applyCommentAreaVisibility: function ($choiceItemGroup) {
        const $otherItem = $choiceItemGroup.find('.o_survey_js_form_other_comment');
        const $commentInput = $choiceItemGroup.find('textarea[type="text"]');

        if ($otherItem.prop('checked') || $commentInput.hasClass('o_survey_comment')) {
            $commentInput.each((idx, $input) => $input.disabled = false);
            $commentInput.closest('.o_survey_comment_container').removeClass('d-none');
            if ($otherItem.prop('checked')) {
                $commentInput.focus();
            }
        } else {
            $commentInput.val('');
            $commentInput.closest('.o_survey_comment_container').addClass('d-none');
            $commentInput.each((idx, $input) => $input.disabled = true);
        }
    },


   /**
    * Will automatically focus on the first input to allow the user to complete directly the survey,
    * without having to manually get the focus (only if the input has the right type - can write something inside -
    * and if the device is not a mobile device to avoid missing information when the soft keyboard is opened)
    */
    _focusOnFirstInput: function () {
        var $firstTextInput = this.$('.js_question-wrapper').first()  // Take first question
                              .find("input[type='text'],input[type='number'],textarea")  // get 'text' inputs
                              .filter('.form-control')  // needed for the auto-resize
                              .not('.o_survey_comment');  // remove inputs for comments that does not count as answers
        if ($firstTextInput.length > 0 && !uiUtils.isSmall()) {
            $firstTextInput.focus();
        }
    },

    /**
    * This method check if the current tab is the master tab at the bus level.
    * If not, the survey could not receive next question notification anymore from session manager.
    * We then ask the participant to close all other tabs on the same hostname before letting them continue.
    *
    * @private
    */
    _checkisOnMainTab: function () {
        var isOnMainTab = this.call('multi_tab', 'isOnMainTab');
        var $errorModal = this.$('#MasterTabErrorModal');
        if (isOnMainTab) {
            // Force reload the page when survey is ready to be followed, to force restart long polling
            if (this.shouldReloadMasterTab) {
                window.location.reload();
            }
           return true;
        } else if (!$errorModal.modal._isShown) {
            $errorModal.find('.text-danger').text(window.location.hostname);
            $errorModal.modal('show');
        }
        return false;
    },

    // CONDITIONAL QUESTIONS MANAGEMENT TOOLS
    // -------------------------------------------------------------------------

    /**
     * For single and multiple choice questions, propagate questions visibility
     * based on conditional questions and (de)selected triggers
     *
     * @param {JQuery<HTMLElement>} $target
     * @param {JQuery<HTMLElement>} $choiceItemGroup
     * @returns {boolean} Whether the question is considered completed
     */
    _checkConditionalQuestionsConfiguration: function ($target, $choiceItemGroup) {
        let isQuestionComplete = false;
        const $matrixBtn = $target.closest('.o_survey_matrix_btn');
        if ($target.attr('type') === 'radio') {
            if ($matrixBtn.length > 0) {
                $matrixBtn.closest('tr').find('td').removeClass('o_survey_selected');
                if ($target.is(':checked')) {
                    $matrixBtn.addClass('o_survey_selected');
                }
                if (this.options.questionsLayout === 'page_per_question') {
                    var subQuestionsIds = $matrixBtn.closest('table').data('subQuestions');
                    var completedQuestions = [];
                    subQuestionsIds.forEach((id) => {
                        if (this.$('tr#' + id).find('input:checked').length !== 0) {
                            completedQuestions.push(id);
                        }
                    });
                    isQuestionComplete = completedQuestions.length === subQuestionsIds.length;
                }
            } else {
                const previouslySelectedAnswer = $choiceItemGroup.find('label.o_survey_selected');
                previouslySelectedAnswer.removeClass('o_survey_selected');
                const previouslySelectedAnswerId = previouslySelectedAnswer.find('input').val();
                if (previouslySelectedAnswerId && this.options.questionsLayout !== 'page_per_question') {
                    this.selectedAnswers.splice(this.selectedAnswers.indexOf(parseInt(previouslySelectedAnswerId)), 1);
                }

                const newlySelectedAnswer = $target.closest('label');
                const newlySelectedAnswerId = $target.val();
                const isNewSelection = newlySelectedAnswerId !== previouslySelectedAnswerId;
                if (isNewSelection) {
                    newlySelectedAnswer.addClass('o_survey_selected');
                    isQuestionComplete = this.options.questionsLayout === 'page_per_question';
                    if (!isQuestionComplete) {
                        this.selectedAnswers.push(parseInt(newlySelectedAnswerId));
                    }
                }

                if (this.options.questionsLayout !== 'page_per_question') {
                    const conditionalQuestionsToRecomputeVisibility = new Set(
                        (this.options.triggeredQuestionsByAnswer[previouslySelectedAnswerId] || [])
                            .concat(this.options.triggeredQuestionsByAnswer[newlySelectedAnswerId] || [])
                    )
                    this._applyConditionalQuestionsVisibility(conditionalQuestionsToRecomputeVisibility)
                }
            }
        } else {  // $target.attr('type') === 'checkbox'
            if ($matrixBtn.length > 0) {
                $matrixBtn.toggleClass('o_survey_selected', !$matrixBtn.hasClass('o_survey_selected'));
            } else {
                const $label = $target.closest('label');
                $label.toggleClass('o_survey_selected', !$label.hasClass('o_survey_selected'));
                const answerId = $target.val();

                if (this.options.questionsLayout !== 'page_per_question') {
                    $label.hasClass('o_survey_selected')
                        ? this.selectedAnswers.push(parseInt(answerId))
                        : this.selectedAnswers.splice(this.selectedAnswers.indexOf(parseInt(answerId)), 1);
                    this._applyConditionalQuestionsVisibility(this.options.triggeredQuestionsByAnswer[answerId]);
                }
            }
        }
        return isQuestionComplete;
    },

    /**
     * Apply visibility rules of conditional questions.
     *
     * @param {Number[] | String[] | Set | undefined} questionIds Conditional questions ids
     */
    _applyConditionalQuestionsVisibility: function(questionIds) {
        if (!questionIds || (!questionIds.length && !questionIds.size)) {
            return;
        }
        for (const questionId of questionIds) {
            const dependingQuestion = document.querySelector(`.js_question-wrapper[id="${questionId}"]`);
            if (!dependingQuestion) {  // Could be on different page
                continue;
            }
            const hasNoSelectedTriggers = !this.options.triggeringAnswersByQuestion[questionId]
                .some(answerId => this.selectedAnswers.includes(parseInt(answerId)));
            dependingQuestion.classList.toggle('d-none', hasNoSelectedTriggers);
            if (hasNoSelectedTriggers) {
                // Clear / Un-select all the input from the given question
                // + propagate conditional hierarchy by triggering change on choice inputs.
                $(dependingQuestion).find('input').each(function () {
                    if ($(this).attr('type') === 'text' || $(this).attr('type') === 'number') {
                        $(this).val('');
                    } else if ($(this).prop('checked')) {
                        $(this).prop('checked', false).change();
                    }
                });
                $(dependingQuestion).find('textarea').val('');
            }
        }
    },

    /**
    * Get questions that are not supposed to be answered by the user.
    * Those are the ones triggered by answers that the user did not selected.
    *
    * @private
    */
    _getInactiveConditionalQuestionIds: function () {
        const inactiveQuestionIds = [];
        for (const [questionId, answerIds] of Object.entries(this.options.triggeringAnswersByQuestion || {})) {
            if (!answerIds.some(answerId => this.selectedAnswers.includes(parseInt(answerId)))) {
                inactiveQuestionIds.push(parseInt(questionId));
            }
        }
        return inactiveQuestionIds;
    },

    // ANSWERS TOOLS
    // -------------------------------------------------------------------------

    _showCorrectAnswers: function(correctAnswers, submitPromise, options) {
        // Display the correct answers
        Object.keys(correctAnswers).forEach(questionId => this._showQuestionAnswer(correctAnswers, questionId));
        // Make the form completely readonly
        const form = document.querySelector('form');
        form.querySelectorAll('input, textarea, label, td')?.forEach(node => {
            node.blur();
            node.classList.add("pe-none");
        });
        // Replace the Submit button by a Next button
        form.querySelector('button[type="submit"]').classList.add('d-none');
        const nextPageBtn = form.querySelector('button[id="next_page"]');
        nextPageBtn.classList.remove('d-none');
        nextPageBtn.addEventListener('click', () => {
            this._nextScreen(submitPromise, options);
        });
        // Replacing the original onKeyDown listener to block everything except for the
        // enter or arrow right key down events trigerring the next page display
        const nextPageKeydownListener = (event) => {
            if (event.code === 'Enter' || event.code === 'ArrowRight') {
                // Restore original keydown listener
                document.removeEventListener('keydown', nextPageKeydownListener);
                document.addEventListener('keydown', this.documentKeydownListener);
                this._nextScreen(submitPromise, options);
            }
        }
        document.removeEventListener('keydown', this.documentKeydownListener);
        document.addEventListener('keydown', nextPageKeydownListener);
    },

    _showQuestionAnswer: function(correctAnswers, questionId) {
        const correctAnswer = correctAnswers[questionId];
        const questionWrapper = document.querySelector(`.js_question-wrapper[id="${questionId}"]`);
        const answerWrapper = questionWrapper.querySelector('.o_survey_answer_wrapper');
        const questionType = questionWrapper.querySelector('[data-question-type]').dataset.questionType;

        if (['numerical_box', 'date', 'datetime'].includes(questionType)) {
            const input = answerWrapper.querySelector('input');
            let isCorrect;
            if (questionType == 'numerical_box') {
                isCorrect = input.valueAsNumber === correctAnswer;
            } else if (questionType == 'datetime') {
                const datetime = parseDateTime(input.value);
                const value = datetime ? datetime.setZone("utc").toFormat("MM/dd/yyyy HH:mm:ss", { numberingSystem: "latn" }) : '';
                isCorrect = value === correctAnswer;
            } else {
                isCorrect = input.value === correctAnswer;
            }
            answerWrapper.classList.add(`bg-${isCorrect ? 'success' : 'danger'}`);
        }
        else if (['simple_choice_radio', 'multiple_choice'].includes(questionType)) {
            answerWrapper.querySelectorAll('.o_survey_choice_btn').forEach((button) => {
                const answerId = button.querySelector('input').value;
                const isCorrect = correctAnswer.includes(parseInt(answerId));
                button.classList.add(`bg-${isCorrect ? 'success' : 'danger'}`, 'text-white');
                // For the user incorrect answers, replace the empty check icon by a crossed check icon
                if (!isCorrect && button.classList.contains('o_survey_selected')) {
                    let fromIcon = 'fa-check-circle';
                    let toIcon = 'fa-times-circle';
                    if (questionType == 'multiple_choice') {
                        fromIcon = 'fa-check-square';
                        toIcon = 'fa-times-rectangle'; // fa-times-square doesn't exist in fontawesome 4.7
                    }
                    button.querySelector(`i.${fromIcon}`)?.classList.replace(fromIcon, toIcon);
                }
            });
        }
    },

    // ERRORS TOOLS
    // -------------------------------------------------------------------------

    _showErrors: function (errors) {
        var self = this;
        var errorKeys = Object.keys(errors || {});
        errorKeys.forEach(key => {
            self.$("#" + key + '>.o_survey_question_error').append($('<span>', {text: errors[key]})).addClass("slide_in");
            if (errorKeys[0] === key) {
                self._scrollToError(self.$('.js_question-wrapper#' + key));
            }
        });
    },

    /**
     * This method is used to scroll to error generated in the backend.
     * (Those errors are displayed when the user skip mandatory question(s))
     */
    _scrollToFirstError: function() {
        const errorElem = this.el.querySelector('.o_survey_question_error :not(:empty)');
        errorElem?.scrollIntoView();
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
        this.el.querySelectorAll('.o_survey_question_matrix th.bg-danger').forEach((row) => {
            row.classList.remove('bg-danger');
        });
    },

});

export default publicWidget.registry.SurveyFormWidget;
