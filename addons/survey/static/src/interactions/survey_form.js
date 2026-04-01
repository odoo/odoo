import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    deserializeDate,
    deserializeDateTime,
    parseDateTime,
    parseDate,
    serializeDateTime,
    serializeDate,
} from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { resizeTextArea } from "@web/core/utils/autoresize";
import { Interaction } from "@web/public/interaction";
import { redirect } from "@web/core/utils/urls";
import { scrollTo } from "@web/core/utils/scrolling";

import SurveyPreloadImageMixin from "@survey/js/survey_preload_image_mixin";
import { fadeIn, fadeOut } from "@survey/utils";

const { DateTime } = luxon;

export class SurveyForm extends Interaction {
    static selector = ".o_survey_form";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _background: () => document.querySelector("div.o_survey_background"),
    };
    dynamicContent = {
        _document: {
            "t-on-keydown": (ev) => {
                if (this.listenOnKeydown) {
                    this.onKeyDown(ev);
                }
            },
        },
        ".o_survey_lang_selector": { "t-on-change": this.onLanguageChange },
        ".o_survey_form_choice_item": { "t-on-change": this.onChoiceItemChange },
        ".o_survey_matrix_btn": { "t-on-click": this.onMatrixButtonClick },
        "input[type='radio']": { "t-on-click": this.onRadioChoiceClick },
        "button[type='submit']": { "t-on-click": this.onSubmit },
        ".o_survey_choice_img img": { "t-on-click": this.onChoiceImageClick },
        ".o_survey_breadcrumb_container .breadcrumb-item a": {
            "t-on-click.prevent": this.onBreadcrumbClick,
        },
        ".o_survey_breadcrumb_container": {
            "t-att-class": () => ({ "d-none": !this.showBreadcrumb }),
        },
        _background: {
            "t-att-class": () => ({ o_survey_background_transition: this.background.transition }),
            "t-att-style": () => {
                if (this.background.shouldUpdate) {
                    return {
                        "background-image": `url("${this.background.image}")`,
                    };
                }
                return {};
            },
        },
    };

    setup() {
        this.dialog = this.services.dialog;
        this.fadeInOutDelay = 400;
        this.formEl = this.el.querySelector("form.o_survey-fill-form");
        const optionsData = this.el.querySelector("form.o_survey-fill-form").dataset;
        this.options = {
            scoringType: optionsData.scoringType,
            answerToken: optionsData.answerToken,
            surveyToken: optionsData.surveyToken,
            usersCanGoBack: !!optionsData.usersCanGoBack,
            sessionInProgress: !!optionsData.sessionInProgress,
            isStartScreen: !!optionsData.isStartScreen,
            readonly: !!optionsData.readonly,
            hasAnswered: !!optionsData.hasAnswered,
            isPageDescription: !!optionsData.isPageDescription,
            questionsLayout: optionsData.questionsLayout,
            triggeredQuestionsByAnswer: JSON.parse(optionsData.triggeredQuestionsByAnswer),
            triggeringAnswersByQuestion: JSON.parse(optionsData.triggeringAnswersByQuestion),
            selectedAnswers: JSON.parse(optionsData.selectedAnswers),
            refreshBackground: !!optionsData.refreshBackground,
        };
        this.readonly = this.options.readonly;
        this.selectedAnswers = this.options.selectedAnswers;
        this.imgZoomer = false;
        this.listenOnKeydown = !this.readonly;
        this.nextScreenResult;
        this.showBreadcrumb = false;
        this.notificationDestructors = [];
        this.background = {
            transition: false,
            image: "",
            shouldUpdate: false,
        };

        // NOTE: the following few lines are only there to solve a bug where when
        // the user changes the language of the survey and the page is reloaded,
        // the background image disappears
        // the language-changed param is added to the url in onLanguageChange
        const url = new URL(window.location.href);
        const languageChanged = url.searchParams.has("language-changed");
        if (languageChanged) {
            url.searchParams.delete("language-changed");
            window.history.replaceState({}, "", url.href);
        }
        const backgroundUrl = document
            .querySelector("div.o_survey_background")
            .style.backgroundImage?.slice(4, -1)
            .replace(/['"]/g, "");
        const language = document.querySelector(".o_survey_lang_selector option[selected]")?.value;
        if (languageChanged && backgroundUrl && language) {
            this.background.shouldUpdate = true;
            this.background.image = `/${language}/${backgroundUrl}`;
        }

        this.submitting = false;
        this.breadcrumbData = null;
        // Add Survey cookie to retrieve the survey if you quit the page and restart the survey.
        if (!cookie.get(`survey_${this.options.surveyToken}`)) {
            cookie.set(
                `survey_${this.options.surveyToken}`,
                this.options.answerToken,
                60 * 60 * 24,
                "optional"
            );
        }
        if (
            this.options.sessionInProgress &&
            (this.options.isStartScreen ||
                this.options.hasAnswered ||
                this.options.isPageDescription)
        ) {
            this.preventEnterSubmit = true;
        }
    }

    async willStart() {
        // initialize session management
        const busService = this.services.bus_service;
        if (this.options.surveyToken && this.options.sessionInProgress) {
            busService.addChannel(this.options.surveyToken);
            await this.checkIsOnMainTab();
            busService.subscribe("next_question", this.onNextQuestionNotification.bind(this));
            busService.subscribe("end_session", this.onEndSessionNotification.bind(this));
        }
        this.initChoiceItems();
        this.initTextArea();
        this.enableSubmitButtons();
        this.focusOnFirstInput();
    }

    start() {
        // These elements are not children of this.el
        this.surveyProgressEl = document.querySelector(".o_survey_progress_wrapper");
        this.surveyNavigationEl = document.querySelector(".o_survey_navigation_wrapper");
        if (!this.options.isStartScreen && !this.readonly) {
            this.initTimer();
            this.initBreadcrumb();
        }
        this.updateNavigationListeners();
        this.updateContent(); // necessary to show/hide breadcrumb
    }

    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handle keyboard navigation:
     * - 'enter' or 'arrow-right' => submit form
     * - 'arrow-left' => submit form (but go back backwards)
     * - other alphabetical character ('a', 'b', ...)
     *   Select the related option in the form (if available)
     */
    onKeyDown(ev) {
        const ctrlKeyClicked = ev.ctrlKey || ev.metaKey;
        const inputFocused =
            document.activeElement.tagName.toLowerCase() === "input" && document.hasFocus();

        if (
            ["one_page", "page_per_section"].includes(this.options.questionsLayout) &&
            !this.options.isStartScreen
        ) {
            if (inputFocused && ev.key === "Enter") {
                ev.preventDefault();
            }
            if (!ctrlKeyClicked || ev.key !== "Enter") {
                return;
            }
        }

        // If in session mode and question already answered, do not handle keydown
        if (this.el.querySelector("fieldset[disabled='disabled']")) {
            return;
        }
        // Disable all navigation keys when zoom modal is open, except the ESC.
        if (this.imgZoomer && !this.imgZoomer.isDestroyed() && ev.key !== "Escape") {
            return;
        }

        const textareaFocused =
            document.activeElement.tagName.toLowerCase() === "textarea" && document.hasFocus();

        // If user is answering a text input, do not handle keydown
        // CTRL+enter will force submission (meta key for Mac)
        if ((textareaFocused || inputFocused) && (!ctrlKeyClicked || ev.key !== "Enter")) {
            return;
        }

        if (ev.key === "Enter" || ev.key === "ArrowRight") {
            // Enter or arrow-right: go Next
            ev.preventDefault();
            if (this.showingCorrectAnswers) {
                this.showingCorrectAnswers = false;
                this.nextScreen(this.nextScreenPromise, this.nextScreenOptions);
                return;
            }
            if (this.preventEnterSubmit) {
                return;
            }
            this.submitForm({
                isFinish: !!this.el.querySelector("button[value='finish']"),
                nextSkipped: this.el.querySelector("button[value='next_skipped']")
                    ? ev.key === "Enter"
                    : false,
            });
            return;
        }
        if (ev.key === "ArrowLeft") {
            // arrow-left: previous (if available)
            if (this.showingCorrectAnswers) {
                return;
            }
            // It's easier to actually click on the button (if in the DOM) as it contains necessary
            // data that are used in the event handler.
            // Again, global selector necessary since the navigation is outside of the form.
            document.querySelector(".o_survey_navigation_submit[value='previous']")?.click();
            return;
        }
        if (this.showingCorrectAnswers || !ev.key.match(/[a-z]/i)) {
            return;
        }
        const choiceInputEl = this.el.querySelector(
            `input[data-selection-key=${ev.key.toUpperCase()}]`
        );
        if (choiceInputEl) {
            choiceInputEl.checked = !choiceInputEl.checked;
            this.triggerEvent(choiceInputEl, "change");
            // Avoid selection key to be typed into the textbox if 'other' is selected by key
            ev.preventDefault();
        }
    }

    /**
     * Handle visibility of comment area and conditional questions
     * The form (page) is then automatically submitted if:
     * - Survey is configured with one page per question and participants are allowed to go back,
     * - It is not the last question of the survey,
     * - The question is not waiting for a comment (with "Other" answer),
     *
     * @param {Event} ev
     */
    async onChoiceItemChange(ev) {
        const targetEl = ev.currentTarget;
        let questionEl = targetEl.closest(".o_survey_form_choice");
        if (!questionEl) {
            // if the question is of type matrix, then targetEl does not have a parent with class o_survey_form_choice
            questionEl = targetEl.closest(".o_survey_question_matrix");
            if (!questionEl) {
                return;
            }
        }

        // Update survey button to "continue" if the current page/question is the last (without accounting for
        // its own conditional questions) but a selected answer is triggering a conditional question on a next page.
        const surveyLastTriggeringAnswers = this.el.querySelector(".o_survey_form_content_data")
            .dataset.surveyLastTriggeringAnswers;
        if (surveyLastTriggeringAnswers) {
            const currentSelectedAnswers = Array.from(
                this.el.querySelectorAll(`
                .o_survey_form_choice[data-question-type='simple_choice_radio'] input:checked,
                .o_survey_form_choice[data-question-type='multiple_choice'] input:checked
            `)
            ).map((input) => parseInt(input.value));
            const submitButton = this.el.querySelector("button[type=submit]");
            if (
                currentSelectedAnswers.some((answerId) =>
                    surveyLastTriggeringAnswers.includes(answerId)
                )
            ) {
                // change to continue
                submitButton.value = "next";
                submitButton.textContent = _t("Continue");
                submitButton.classList.replace("btn-secondary", "btn-primary");
            } else {
                // change to submit
                submitButton.value = "finish";
                submitButton.textContent = _t("Submit");
                submitButton.classList.replace("btn-primary", "btn-secondary");
            }
        }
        this.applyCommentAreaVisibility(questionEl);
        const isQuestionComplete = this.checkConditionalQuestionsConfiguration(
            targetEl,
            questionEl
        );

        // if the question is complete, not the last and does not have a comment, we can automatically continue to the next one
        if (!isQuestionComplete || !this.options.usersCanGoBack) {
            return;
        }
        const isLastQuestion = !!this.el.querySelector("button[value='finish']");
        if (isLastQuestion) {
            return;
        }
        const questionHasComment =
            targetEl.classList.contains("o_survey_js_form_other_comment") ||
            targetEl.closest(".js_question-wrapper").querySelector(".o_survey_comment");
        if (!questionHasComment) {
            await this.submitForm({
                nextSkipped: !!questionEl.dataset.isSkippedQuestion,
            });
        }
    }

    /**
     * Called when an image on an answer in multi-answers question is clicked.
     * @param {Event} ev
     */
    onChoiceImageClick(ev) {
        if (!uiUtils.isSmall()) {
            // On large screen, it prevents the answer to be selected as the user only want to enlarge the image.
            // We don't do it on small device as it can be hard to click outside the picture to select the answer.
            ev.preventDefault();
        }
        this.renderAt(
            "survey.survey_image_zoomer",
            { sourceImage: ev.currentTarget.src },
            document.body
        );
    }

    removeTimer() {
        if (this.timerEl) {
            this.services["public.interactions"].stopInteractions(this.timerEl);
            this.timerEl.remove();
        }
    }

    replaceContent(content, locationEl) {
        const parser = new DOMParser();
        const contentEls = parser.parseFromString(content, "text/html").body.children;
        locationEl.replaceChildren();
        while (contentEls.length > 0) {
            this.insert(contentEls.item(0), locationEl);
        }
    }

    /**
     * Invert the related input's "checked" property.
     * This will tick or untick the option (based on the previous state).
     */
    onMatrixButtonClick(ev) {
        if (this.readonly) {
            return;
        }
        const targetEl = ev.currentTarget;
        const inputEl = targetEl.querySelector("input");
        inputEl.checked = !inputEl.checked;
        this.triggerEvent(inputEl, "change");
    }

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
     *   We also trigger the 'change' event to go into 'onChoiceItemChange'.
     */
    onRadioChoiceClick(ev) {
        const targetEl = ev.currentTarget;
        if (targetEl.classList.contains("o_survey_form_choice_item_selected")) {
            targetEl.checked = false;
            targetEl.classList.remove("o_survey_form_choice_item_selected");
            this.triggerEvent(targetEl, "change");
        } else {
            this.el
                .querySelector(
                    `input[type="radio"][name="${targetEl.getAttribute(
                        "name"
                    )}"].o_survey_form_choice_item_selected`
                )
                ?.classList.remove("o_survey_form_choice_item_selected");
            targetEl.classList.add("o_survey_form_choice_item_selected");
        }
    }

    onSubmit(ev) {
        ev.preventDefault();
        const targetEl = ev.currentTarget;
        if (targetEl.value === "previous") {
            this.submitForm({ previousPageId: parseInt(targetEl.dataset.previousPageId) });
        } else if (targetEl.value === "next_skipped") {
            this.submitForm({ nextSkipped: true });
        } else if (targetEl.value === "finish" && !this.options.sessionInProgress) {
            // Adding pop-up before the survey is submitted when not in live session
            this.dialog.add(ConfirmationDialog, {
                title: _t("Submit confirmation"),
                body: _t("Are you sure you want to submit the survey?"),
                confirmLabel: _t("Submit"),
                confirm: () => {
                    this.waitForTimeout(() => this.submitForm({ isFinish: true }), 0);
                },
                cancel: () => {},
            });
        } else {
            this.submitForm();
        }
    }

    onBreadcrumbClick(ev) {
        const previousPageId = Number(ev.currentTarget.closest(".breadcrumb-item").dataset.pageId);
        this.submitForm({ previousPageId });
    }

    /**
     * Handle some extra computation to find a suitable "fadeInOutDelay" based
     * on the delay between the time of the question change by the host and the
     * time of reception of the event. This will allow us to account for a
     * little bit of server lag (up to 1 second) while giving everyone a fair
     * experience on the quiz.
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
     * @param {object} notification notification of type `next_question` as
     * specified by the bus.
     */
    onNextQuestionNotification(notification) {
        let serverDelayMS = (DateTime.now().toSeconds() - notification.question_start) * 1000;
        if (serverDelayMS < 0) {
            serverDelayMS = 0;
        } else if (serverDelayMS > 1000) {
            serverDelayMS = 1000;
        }
        this.fadeInOutDelay = (1000 - serverDelayMS) / 2;
        this.goToNextPage();
    }

    /**
     * Handle the `end_session` bus event. This will fade out the current page
     * and fade in the end screen.
     *
     */
    onEndSessionNotification() {
        if (this.options.isStartScreen) {
            // can happen when triggering the same survey session multiple times
            // we received an "old" end_session event that needs to be ignored
            return;
        }
        this.fadeInOutDelay = 400;
        this.goToNextPage(true);
    }

    onLanguageChange() {
        const languageCode = this.el.querySelector(
            ".o_survey_lang_selector[name='lang_code']"
        ).value;
        const pathName = document.location.pathname;
        const indexOfSurvey = pathName.indexOf("/survey/");
        if (indexOfSurvey >= 0) {
            const url = new URL(window.location.href);
            url.pathname = `/${languageCode}${pathName.substring(indexOfSurvey)}`;
            url.searchParams.set("language-changed", true);
            redirect(url.href);
        }
    }

    /**
     * Go to the next page of the survey.
     *
     * @param {boolean} isFinish Whether the survey is done or not
     */
    goToNextPage(isFinish = false) {
        fadeOut(this.el.querySelectorAll(".o_survey_main_title, .o_lang_selector"), 400);
        this.preventEnterSubmit = false;
        this.readonly = false;
        this.nextScreen(
            rpc(`/survey/next_question/${this.options.surveyToken}/${this.options.answerToken}`),
            {
                initTimer: true,
                isFinish,
            }
        );
    }

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
     * @param {Boolean} [options.nextSkipped] navigates to next skipped page or question
     * @param {Boolean} [options.skipValidation] skips JS validation
     * @param {Boolean} [options.initTime] will force the re-init of the timer after next
     *   screen transition
     * @param {Boolean} [options.isFinish] fades out breadcrumb and timer
     */
    async submitForm(options = {}) {
        if (this.submitting) {
            return;
        }
        this.submitting = true;
        const params = {};
        if (options.previousPageId) {
            params.previous_page_id = options.previousPageId;
        }
        if (options.nextSkipped) {
            params.next_skipped_page_or_question = true;
        }
        let route = "/survey/submit";
        if (this.options.isStartScreen) {
            params.lang_code = this.el.querySelector(
                ".o_survey_lang_selector[name='lang_code']"
            ).value;
            route = "/survey/begin";
            // Hide survey title in 'page_per_question' layout: it takes too much space
            if (this.options.questionsLayout === "page_per_question") {
                fadeOut(this.el.querySelector(".o_survey_main_title"), 400);
            }
            fadeOut(this.el.querySelector(".o_survey_lang_selector"), 400);
        } else {
            const formData = new FormData(this.formEl);
            if (!options.skipValidation) {
                if (!this.validateForm(this.formEl, formData)) {
                    this.submitting = false;
                    return;
                }
            }
            this.prepareSubmitValues(formData, params);
        }

        if (this.options.sessionInProgress) {
            // reset the fadeInOutDelay when attendee is submitting form
            this.fadeInOutDelay = 400;
            // prevent user from clicking on matrix options when form is submitted
            this.readonly = true;
        }

        const submitPromise = rpc(
            `${route}/${this.options.surveyToken}/${this.options.answerToken}`,
            params
        );

        if (
            !this.options.isStartScreen &&
            this.options.scoringType === "scoring_with_answers_after_page"
        ) {
            const [correctAnswers] = await this.waitFor(submitPromise);
            if (
                Object.keys(correctAnswers).length &&
                this.el.querySelector(".js_question-wrapper")
            ) {
                this.showCorrectAnswers(correctAnswers, submitPromise, options);
                this.submitting = false;
                return;
            }
        }
        await this.nextScreen(submitPromise, options);
        this.submitting = false;
    }

    /**
     * Will fade out / fade in the next screen based on passed promise and options.
     *
     * @param {Promise} nextScreenPromise
     * @param {Object} options see 'submitForm' for details
     */
    async nextScreen(nextScreenPromise, options) {
        const selectorsToFadeout = [".o_survey_form_content"];
        if (options.isFinish && !this.nextScreenResult?.has_skipped_questions) {
            // Fade out the top title
            document.querySelector('.o_survey_main_title_fade')?.classList.replace("opacity-100", "opacity-0");
            
            selectorsToFadeout.push(".breadcrumb", ".o_survey_timer");
            cookie.delete(`survey_${this.options.surveyToken}`);
        }
        const fadeOutPromise = this.waitFor(
            fadeOut(this.el.querySelectorAll(selectorsToFadeout.join(",")), this.fadeInOutDelay)
        );
        if (this.options.refreshBackground) {
            this.background.transition = true;
        }

        const nextScreenWithBackgroundPromise = (async () => {
            const [, result] = await nextScreenPromise;
            this.nextScreenResult = result;
            if (this.options.refreshBackground && result.background_image_url) {
                return SurveyPreloadImageMixin._preloadBackground(result.background_image_url);
            } else {
                return Promise.resolve();
            }
        })();

        await this.waitFor(Promise.all([fadeOutPromise, nextScreenWithBackgroundPromise]));
        return this.onNextScreenDone(options);
    }

    /**
     * Handle server side validation and display eventual error messages.
     *
     * @param {Object} options see 'submitForm' for details
     */
    onNextScreenDone(options) {
        const result = this.nextScreenResult;
        if (
            (!(options && options.isFinish) || result.has_skipped_questions) &&
            !this.options.sessionInProgress
        ) {
            this.preventEnterSubmit = false;
        }
        if (result && result.fields && result.error === "validation") {
            fadeIn(this.el.querySelector(".o_survey_form_content"), 0);
            this.showErrors(result.fields);
            return;
        }
        if (!result || result.error) {
            this.notificationDestructors.push(
                this.services.notification.add(
                    _t("There was an error during the validation of the survey."),
                    { type: "danger", sticky: true }
                )
            );
            return;
        }
        const formContentEl = this.el.querySelector(".o_survey_form_content");
        this.replaceContent(result.survey_content, formContentEl);

        if (result.survey_progress && this.surveyProgressEl) {
            this.replaceContent(result.survey_progress, this.surveyProgressEl);
        } else if (options.isFinish && this.surveyProgressEl) {
            this.surveyProgressEl.remove();
        }

        if (result.survey_navigation && this.surveyNavigationEl) {
            this.replaceContent(result.survey_navigation, this.surveyNavigationEl);
            this.updateNavigationListeners();
        }

        // Hide timer if end screen (if page_per_question in case of conditional questions)
        if (
            this.options.questionsLayout === "page_per_question" &&
            this.el.querySelector(".o_survey_finished")
        ) {
            options.isFinish = true;
        }

        // Force recompute the title's display condition and fade it in
        if (this.options.isStartScreen && this.options.questionsLayout !== 'page_per_question') {
            document.querySelector('.o_survey_main_title_fade')?.classList.replace("opacity-0", "opacity-100");
        }

        if (this.options.isStartScreen || (options && options.initTimer)) {
            this.initTimer();
            this.options.isStartScreen = false;
        } else {
            if (this.options.sessionInProgress) {
                this.removeTimer();
            }
        }
        if (options && options.isFinish && !result.has_skipped_questions) {
            if (this.breadcrumbEl) {
                this.showBreadcrumb = false;
                this.breadcrumbEl.replaceChildren();
            }
            this.removeTimer();
        } else {
            this.updateBreadcrumb();
        }
        this.initChoiceItems();
        this.initTextArea();

        if (this.options.sessionInProgress && this.options.isPageDescription) {
            // Prevent enter submit if we're on a page description (there is nothing to submit)
            this.preventEnterSubmit = true;
        }
        // Background management - reset background overlay opacity to 0.7 to discover next background.
        if (this.options.refreshBackground) {
            this.background.transition = false;
            this.background.image = result.background_image_url;
            this.background.shouldUpdate = true;
        }
        fadeIn(formContentEl, this.fadeInOutDelay);
        this.enableSubmitButtons();
        this.focusOnFirstInput();
        this.scrollTop(); // must be after focus
        this.scrollToFirstError();
    }

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
     */
    validateForm(formEl, formData) {
        const errors = {};
        const validationEmailMsg = _t("This answer must be an email address.");
        const validationDateMsg = _t("This is not a date");
        this.resetErrors();
        const data = {};
        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }
        const inactiveQuestionIds = this.options.sessionInProgress
            ? []
            : this.getInactiveConditionalQuestionIds();
        for (const inputEl of formEl.querySelectorAll("[data-question-type]")) {
            const questionWrapperEl = inputEl.closest(".js_question-wrapper");
            const questionId = questionWrapperEl.id;
            if (inactiveQuestionIds.includes(parseInt(questionId))) {
                continue;
            }
            const questionRequired = questionWrapperEl.hasAttribute("data-required");
            const constrErrorMsg = questionWrapperEl.dataset.constrErrorMsg || "";
            const validationErrorMsg = questionWrapperEl.dataset.validationErrorMsg || "";
            const inputData = {
                questionType: inputEl.dataset.questionType,
                validationLengthMin: Number(inputEl.dataset.validationLengthMin),
                validationLengthMax: Number(inputEl.dataset.validationLengthMax),
                validationFloatMin: Number(inputEl.dataset.validationFloatMin),
                validationFloatMax: Number(inputEl.dataset.validationFloatMax),
                minDate: inputEl.dataset.minDate,
                maxDate: inputEl.dataset.maxDate,
            };
            switch (inputData.questionType) {
                case "char_box":
                    if (questionRequired && !inputEl.value) {
                        errors[questionId] = constrErrorMsg;
                    } else if (
                        inputEl.value &&
                        inputEl.type === "email" &&
                        !this.validateEmail(inputEl.value)
                    ) {
                        errors[questionId] = validationEmailMsg;
                    } else {
                        const lengthMin = inputData.validationLengthMin;
                        const lengthMax = inputData.validationLengthMax;
                        const length = inputEl.value.length;
                        if (lengthMin && (lengthMin > length || length > lengthMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case "text_box":
                    if (questionRequired && !inputEl.value) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
                case "numerical_box":
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else {
                        const floatMin = inputData.validationFloatMin;
                        const floatMax = inputData.validationFloatMax;
                        const value = parseFloat(inputEl.value);
                        if (floatMin && (floatMin > value || value > floatMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case "date":
                case "datetime":
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else if (data[questionId]) {
                        const [parse, deserialize] =
                            inputData.questionType === "date"
                                ? [parseDate, deserializeDate]
                                : [parseDateTime, deserializeDateTime];
                        const date = parse(inputEl.value);
                        if (!date || !date.isValid) {
                            errors[questionId] = validationDateMsg;
                        } else {
                            const maxDate = deserialize(inputData.maxDate);
                            const minDate = deserialize(inputData.minDate);
                            if (
                                (maxDate.isValid && date > maxDate) ||
                                (minDate.isValid && date < minDate)
                            ) {
                                errors[questionId] = validationErrorMsg;
                            }
                        }
                    }
                    break;
                case "scale":
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
                case "simple_choice_radio":
                case "multiple_choice":
                    if (questionRequired) {
                        const textareaEl = questionWrapperEl.querySelector("textarea");
                        if (!data[questionId]) {
                            errors[questionId] = constrErrorMsg;
                        } else if (data[questionId] === "-1" && !textareaEl.value) {
                            // if other has been checked and value is null
                            errors[questionId] = constrErrorMsg;
                        }
                    }
                    break;
                case "matrix":
                    if (questionRequired) {
                        const subQuestionsIds = JSON.parse(
                            inputEl.dataset.subQuestions
                        );
                        // Highlight unanswered rows' header
                        const questionBodySelector = `div[id="${questionId}"] > .o_survey_question_matrix > tbody`;
                        for (const subQuestionId of subQuestionsIds) {
                            if (!(`${questionId}_${subQuestionId}` in data)) {
                                errors[questionId] = constrErrorMsg;
                                this.el
                                    .querySelector(
                                        `${questionBodySelector} > tr[id="${subQuestionId}"] > th`
                                    )
                                    .classList.add("bg-danger");
                            }
                        }
                    }
                    break;
            }
        }
        if (Object.keys(errors).length > 0) {
            this.showErrors(errors);
            return false;
        }
        return true;
    }

    /**
     * Check if the email has an '@', a left part and a right part
     */
    validateEmail(email) {
        const emailParts = email.split("@");
        return emailParts.length === 2 && emailParts[0] && emailParts[1];
    }

    // PREPARE SUBMIT TOOLS
    // -------------------------------------------------------------------------
    /**
     * For each type of question, extract the answer from inputs or textarea (comment or answer)
     * @param {FormData} formData
     * @param {Object} params
     */
    prepareSubmitValues(formData, params) {
        for (const [key, value] of formData) {
            if (["csrf_token", "page_id", "question_id", "token"].includes(key)) {
                params[key] = value;
            }
        }

        // Get all question answers by question type
        for (const el of this.el.querySelectorAll("[data-question-type]")) {
            switch (el.dataset.questionType) {
                case "text_box":
                case "char_box":
                    params[el.name] = el.value;
                    break;
                case "numerical_box":
                    params[el.name] = el.value;
                    break;
                case "date":
                case "datetime": {
                    const [parse, serialize] =
                        el.dataset.questionType === "date"
                            ? [parseDate, serializeDate]
                            : [parseDateTime, serializeDateTime];
                    const date = parse(el.value);
                    params[el.name] = date ? serialize(date) : "";
                    break;
                }
                case "scale":
                case "simple_choice_radio":
                case "multiple_choice":
                    params = this.prepareSubmitChoices(params, el, el.dataset.name);
                    break;
                case "matrix":
                    params = this.prepareSubmitAnswersMatrix(params, el);
                    break;
            }
        }
    }

    /**
     *   Prepare choice answer before submitting form.
     *   If the answer is not the 'comment selection' (=Other), calls the prepareSubmitAnswer method to add the answer to the params
     *   If there is a comment linked to that question, calls the prepareSubmitComment method to add the comment to the params
     */
    prepareSubmitChoices(params, parentEl, questionId) {
        for (const el of parentEl.querySelectorAll("input:checked")) {
            if (el.value !== "-1") {
                params = this.prepareSubmitAnswer(params, questionId, el.value);
            }
        }
        params = this.prepareSubmitComment(params, parentEl, questionId, false);
        return params;
    }

    /**
     *   Prepare matrix answers before submitting form.
     *   This method adds matrix answers one by one and add comment if any to a params key,value like :
     *   params = { 'matrixQuestionId' : {'rowId1': [colId1, colId2,...], 'rowId2': [colId1, colId3, ...], 'comment': comment }}
     */
    prepareSubmitAnswersMatrix(params, matrixTable) {
        for (const el of matrixTable.querySelectorAll("input:checked")) {
            params = this.prepareSubmitAnswerMatrix(
                params,
                matrixTable.dataset.name,
                Number(el.dataset.rowId),
                el.value
            );
        }
        params = this.prepareSubmitComment(
            params,
            matrixTable.closest(".js_question-wrapper"),
            matrixTable.dataset.name,
            true
        );
        return params;
    }

    /**
     *   Prepare answer before submitting form if question type is matrix.
     *   This method regroups answers by question and by row to make an object like :
     *   params = { 'matrixQuestionId' : { 'rowId1' : [colId1, colId2,...], 'rowId2' : [colId1, colId3, ...] } }
     */
    prepareSubmitAnswerMatrix(params, questionId, rowId, colId, isComment) {
        const value = questionId in params ? params[questionId] : {};
        if (isComment) {
            value["comment"] = colId;
        } else {
            if (rowId in value) {
                value[rowId].push(colId);
            } else {
                value[rowId] = [colId];
            }
        }
        params[questionId] = value;
        return params;
    }

    /**
     *   Prepare answer before submitting form (any kind of answer - except Matrix -).
     *   This method regroups answers by question.
     *   Lonely answer are directly assigned to questionId. Multiple answers are regrouped in an array:
     *   params = { 'questionId1' : lonelyAnswer, 'questionId2' : [multipleAnswer1, multipleAnswer2, ...] }
     */
    prepareSubmitAnswer(params, questionId, value) {
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
    }

    /**
     *   Prepare comment before submitting form.
     *   This method extract the comment, encapsulate it in a dict and calls the prepareSubmitAnswer methods
     *   with the new value. At the end, the result looks like :
     *   params = { 'questionId1' : {'comment': commentValue}, 'questionId2' : [multipleAnswer1, {'comment': commentValue}, ...] }
     */
    prepareSubmitComment(params, parentEl, questionId, isMatrix) {
        for (const el of parentEl.querySelectorAll("textarea")) {
            if (el.value) {
                const value = { comment: el.value };
                if (isMatrix) {
                    params = this.prepareSubmitAnswerMatrix(
                        params,
                        questionId,
                        el.name,
                        el.value,
                        true
                    );
                } else {
                    params = this.prepareSubmitAnswer(params, questionId, value);
                }
            }
        }
        return params;
    }

    // INIT FIELDS TOOLS
    // -------------------------------------------------------------------------

    /**
     * Will allow the textarea to resize on carriage return instead of showing scrollbar.
     */
    initTextArea() {
        for (const el of this.el.querySelectorAll("textarea")) {
            resizeTextArea(el);
        }
    }

    initChoiceItems() {
        for (const el of this.el.querySelectorAll("input[type='radio'],input[type='checkbox']")) {
            const matrixButtonEl = el.closest(".o_survey_matrix_btn");
            if (el.checked) {
                const targetEl = matrixButtonEl ? matrixButtonEl : el.closest("label");
                targetEl.classList.add("o_survey_selected");
            }
        }
    }

    /**
     * Will initialize the breadcrumb that handles navigation to a previously filled in page.
     */
    initBreadcrumb() {
        this.breadcrumbEl = this.el.querySelector(".o_survey_breadcrumb_container");
        if (!this.breadcrumbEl) {
            return;
        }
        const data = this.breadcrumbEl.dataset;
        this.breadcrumbData = {
            surveyCanGoBack: !!data.canGoBack,
            pages: JSON.parse(data.pages),
        };
        this.showBreadcrumb = true;
        this.updateBreadcrumb();
    }

    /**
     * Called after survey submit to update the breadcrumb to the right page.
     */
    updateBreadcrumb() {
        if (!this.breadcrumbEl) {
            this.initBreadcrumb();
        } else {
            const pageId = this.el.querySelector("input[name='page_id']")?.value;
            if (pageId) {
                this.breadcrumbEl.replaceChildren();
                this.renderAt(
                    "survey.survey_breadcrumb_template",
                    {
                        currentPageId: parseInt(pageId),
                        ...this.breadcrumbData,
                    },
                    this.breadcrumbEl
                );
            } else {
                this.showBreadcrumb = false;
            }
        }
    }

    initTimer() {
        this.removeTimer();
        const timerDataEl = this.el.querySelector(".o_survey_form_content_data");
        if (!timerDataEl) {
            return;
        }
        const timerData = timerDataEl.dataset;
        const questionTimeLimitReached = !!timerData.questionTimeLimitReached;
        const timeLimitMinutes = Number(timerData.timeLimitMinutes);
        const hasAnswered = !!timerData.hasAnswered;
        if (!questionTimeLimitReached && !hasAnswered && timeLimitMinutes) {
            this.timerEl = document.createElement("span");
            this.timerEl.classList.add("o_survey_timer");
            this.insert(this.timerEl, this.el.querySelector(".o_survey_timer_container"));
            this.addListener(this.timerEl, "time_up", async () => {
                if (this.showingCorrectAnswers) {
                    await this.nextScreen(this.nextScreenPromise, this.nextScreenOptions);
                }
                this.submitForm({
                    skipValidation: true,
                    isFinish: !this.options.sessionInProgress,
                });
            });
        }
    }

    // OTHER TOOLS
    // -------------------------------------------------------------------------

    /**
     * Checks, if the 'other' choice is checked. Applies only if the comment count as answer.
     *   If not checked : Clear the comment textarea, hide and disable it
     *   If checked : enable the comment textarea, show and focus on it
     *
     * @param {HTMLElement} choiceItemGroupEl
     */
    applyCommentAreaVisibility(choiceItemGroupEl) {
        if (!choiceItemGroupEl) {
            return;
        }
        const otherItemEl = choiceItemGroupEl.querySelector(".o_survey_js_form_other_comment");
        const commentInputEl = choiceItemGroupEl.querySelector("textarea[type='text']");
        if (!commentInputEl) {
            return;
        }
        if (otherItemEl?.checked || commentInputEl.classList.contains("o_survey_comment")) {
            commentInputEl.disabled = false;
            commentInputEl.closest(".o_survey_comment_container").classList.remove("d-none");
            if (otherItemEl?.checked) {
                commentInputEl.focus();
            }
        } else {
            commentInputEl.value = "";
            commentInputEl.closest(".o_survey_comment_container").classList.add("d-none");
            commentInputEl.disabled = true;
        }
    }

    /**
     * Will automatically focus on the first input to allow the user to complete directly the survey,
     * without having to manually get the focus (only if the input has the right type - can write something inside -
     * and if the device is not a mobile device to avoid missing information when the soft keyboard is opened)
     */
    focusOnFirstInput() {
        const inputEls =
            this.el
                .querySelector(".js_question-wrapper")
                ?.querySelectorAll("input[type='text'],input[type='number'],textarea") || [];
        let firstTextInputEl = null;
        for (const inputEl of inputEls) {
            if (
                inputEl.classList.contains("form-control") &&
                !inputEl.classList.contains("o_survey_comment")
            ) {
                firstTextInputEl = inputEl;
                break;
            }
        }
        if (firstTextInputEl && !uiUtils.isSmall()) {
            firstTextInputEl.focus();
        }
    }

    async checkIsOnMainTab() {
        const check = async (shouldReloadMasterTab) => {
            if (await this.services.multi_tab.isOnMainTab()) {
                // Force reload the page when survey is ready to be followed, to force restart long polling
                if (shouldReloadMasterTab) {
                    window.location.reload();
                }
                return;
            }
            const checkAgain = () => this.waitForTimeout(() => check(true), 1000);
            this.dialog.add(ConfirmationDialog, {
                title: _t("A problem has occurred"),
                body: _t("To take this survey, please close all other tabs on %(hostname)s",
                    { hostname: window.location.hostname }
                ),
                confirmLabel: _t("Continue here"),
                confirm: checkAgain,
                dismiss: checkAgain,
            });
        };
        return check(false);
    }

    // CONDITIONAL QUESTIONS MANAGEMENT TOOLS
    // -------------------------------------------------------------------------

    /**
     * For single and multiple choice questions, propagate questions visibility
     * based on conditional questions and (de)selected triggers
     *
     * @param {HTMLInputElement} targetEl
     * @param {HTMLElement} choiceItemGroupEl
     * @returns {boolean} Whether the question is considered completed
     */
    checkConditionalQuestionsConfiguration(targetEl, choiceItemGroupEl) {
        let isQuestionComplete = false;
        const matrixButtonEl = targetEl.closest(".o_survey_matrix_btn");
        if (targetEl.type === "radio") {
            if (matrixButtonEl) {
                for (const el of matrixButtonEl.closest("tr")?.querySelectorAll("td") || []) {
                    el.classList.remove("o_survey_selected");
                }
                if (targetEl.checked) {
                    matrixButtonEl.classList.add("o_survey_selected");
                }
                if (this.options.questionsLayout === "page_per_question") {
                    const subQuestionsIds = JSON.parse(
                        matrixButtonEl.closest("table").dataset.subQuestions
                    );
                    const completedQuestions = [];
                    for (const id of subQuestionsIds) {
                        if (
                            this.el.querySelector(`tr[id="${id}"] input:checked`)
                        ) {
                            completedQuestions.push(id);
                        }
                    }
                    isQuestionComplete = completedQuestions.length === subQuestionsIds.length;
                }
            } else {
                const previouslySelectedAnswerEl =
                    choiceItemGroupEl.querySelector("label.o_survey_selected");
                previouslySelectedAnswerEl?.classList.remove("o_survey_selected");
                const previouslySelectedAnswerId =
                    previouslySelectedAnswerEl?.querySelector("input").value;
                if (
                    previouslySelectedAnswerId &&
                    this.options.questionsLayout !== "page_per_question"
                ) {
                    this.selectedAnswers.splice(
                        this.selectedAnswers.indexOf(parseInt(previouslySelectedAnswerId)),
                        1
                    );
                }

                const newlySelectedAnswerEl = targetEl.closest("label");
                const newlySelectedAnswerId = targetEl.value;
                const isNewSelection = newlySelectedAnswerId !== previouslySelectedAnswerId;
                if (isNewSelection) {
                    newlySelectedAnswerEl.classList.add("o_survey_selected");
                    isQuestionComplete = this.options.questionsLayout === "page_per_question";
                    if (!isQuestionComplete) {
                        this.selectedAnswers.push(parseInt(newlySelectedAnswerId));
                    }
                }

                if (this.options.questionsLayout !== "page_per_question") {
                    const toRecompute = (
                        this.options.triggeredQuestionsByAnswer[previouslySelectedAnswerId] || []
                    ).concat(this.options.triggeredQuestionsByAnswer[newlySelectedAnswerId] || []);
                    const conditionalQuestionsToRecomputeVisibility = new Set(toRecompute);
                    this.applyConditionalQuestionsVisibility(
                        conditionalQuestionsToRecomputeVisibility
                    );
                }
            }
        } else {
            // targetEl.type === "checkbox"
            if (matrixButtonEl) {
                matrixButtonEl.classList.toggle("o_survey_selected");
            } else {
                const labelEl = targetEl.closest("label");
                labelEl.classList.toggle("o_survey_selected");
                const answerId = targetEl.value;

                if (this.options.questionsLayout !== "page_per_question") {
                    labelEl.classList.contains("o_survey_selected")
                        ? this.selectedAnswers.push(parseInt(answerId))
                        : this.selectedAnswers.splice(
                              this.selectedAnswers.indexOf(parseInt(answerId)),
                              1
                          );
                    this.applyConditionalQuestionsVisibility(
                        this.options.triggeredQuestionsByAnswer[answerId]
                    );
                }
            }
        }
        return isQuestionComplete;
    }

    /**
     * Apply visibility rules of conditional questions.
     * When layout is "one_page", hide the empty sections (the ones without description and
     * which don't have any question to be displayed because of conditional questions).
     *
     * @param {Number[] | String[] | Set | undefined} questionIds Conditional questions ids
     */
    applyConditionalQuestionsVisibility(questionIds) {
        if (!questionIds || (!questionIds.length && !questionIds.size)) {
            return;
        }
        // Questions visibility
        for (const questionId of questionIds) {
            const dependingQuestionEl = this.el.querySelector(
                `.js_question-wrapper[id="${questionId}"]`
            );
            if (!dependingQuestionEl) {
                // Could be on different page
                continue;
            }
            const hasNoSelectedTriggers = !this.options.triggeringAnswersByQuestion[
                questionId
            ].some((answerId) => this.selectedAnswers.includes(parseInt(answerId)));
            dependingQuestionEl.classList.toggle("d-none", hasNoSelectedTriggers);
            if (hasNoSelectedTriggers) {
                // Clear / Un-select all the input from the given question
                // + propagate conditional hierarchy by triggering change on choice inputs.
                for (const el of dependingQuestionEl.querySelectorAll("input")) {
                    if (el.type === "text" || el.type === "number") {
                        el.value = "";
                    } else if (el.checked) {
                        el.checked = false;
                        this.triggerEvent(el, "change");
                    }
                }
                for (const el of dependingQuestionEl.querySelectorAll("textarea")) {
                    el.value = "";
                }
            }
        }
        // Sections visibility
        if (this.options.questionsLayout === "one_page") {
            const sections = this.el.querySelectorAll(".js_section_wrapper");
            for (const section of sections) {
                if (!section.querySelector(".o_survey_description")) {
                    const hasVisibleQuestions = !!section.querySelector(
                        ".js_question-wrapper:not(.d-none)"
                    );
                    section.classList.toggle("d-none", !hasVisibleQuestions);
                }
            }
        }
    }

    /**
     * Get questions that are not supposed to be answered by the user.
     * Those are the ones triggered by answers that the user did not selected.
     */
    getInactiveConditionalQuestionIds() {
        const inactiveQuestionIds = [];
        for (const [questionId, answerIds] of Object.entries(
            this.options.triggeringAnswersByQuestion || {}
        )) {
            if (!answerIds.some((answerId) => this.selectedAnswers.includes(parseInt(answerId)))) {
                inactiveQuestionIds.push(parseInt(questionId));
            }
        }
        return inactiveQuestionIds;
    }

    // ANSWERS TOOLS
    // -------------------------------------------------------------------------

    showCorrectAnswers(correctAnswers, submitPromise, options) {
        // Display the correct answers
        for (const questionId of Object.keys(correctAnswers)) {
            this.showQuestionAnswer(correctAnswers, questionId);
        }
        // Make the form completely readonly
        const formEl = document.querySelector("form");
        for (const el of formEl.querySelectorAll("input, textarea, label, td")) {
            el.blur();
            el.classList.add("pe-none");
        }

        // This is used to adapt behaviour of onKeyDown
        this.nextScreenPromise = submitPromise;
        this.nextScreenOptions = options;
        this.showingCorrectAnswers = true;

        // Replace the Submit button by a Next button
        formEl.querySelector("button[type='submit']").classList.add("d-none");
        const nextPageButtonEl = formEl.querySelector("button[id='next_page']");
        nextPageButtonEl.classList.remove("d-none");
        this.addListener(nextPageButtonEl, "click", async (ev) => {
            ev.preventDefault();
            this.showingCorrectAnswers = false;
            return this.nextScreen(submitPromise, options);
        });
    }

    showQuestionAnswer(correctAnswers, questionId) {
        const correctAnswer = correctAnswers[questionId];
        const questionWrapperEl = this.el.querySelector(`.js_question-wrapper[id="${questionId}"]`);
        const answerWrapperEl = questionWrapperEl.querySelector(".o_survey_answer_wrapper");
        const questionType =
            questionWrapperEl.querySelector("[data-question-type]").dataset.questionType;

        // Only questions supporting correct answer are present here (ex.: scale question doesn't support it)
        if (["numerical_box", "date", "datetime"].includes(questionType)) {
            const inputEl = answerWrapperEl.querySelector("input");
            let isCorrect;
            if (questionType === "numerical_box") {
                isCorrect = inputEl.valueAsNumber === correctAnswer;
            } else if (questionType === "datetime") {
                const datetime = parseDateTime(inputEl.value);
                const value = datetime
                    ? datetime
                          .setZone("utc")
                          .toFormat("MM/dd/yyyy HH:mm:ss", { numberingSystem: "latn" })
                    : "";
                isCorrect = value === correctAnswer;
            } else {
                isCorrect = inputEl.value === correctAnswer;
            }
            answerWrapperEl.classList.add(`bg-${isCorrect ? "success" : "danger"}`);
        } else if (["simple_choice_radio", "multiple_choice"].includes(questionType)) {
            for (const buttonEl of answerWrapperEl.querySelectorAll(".o_survey_choice_btn")) {
                const answerId = buttonEl.querySelector("input").value;
                const isCorrect = correctAnswer.includes(parseInt(answerId));
                buttonEl.classList.add(`bg-${isCorrect ? "success" : "danger"}`, "text-white");
                // For the user incorrect answers, replace the empty check icon by a crossed check icon
                if (!isCorrect && buttonEl.classList.contains("o_survey_selected")) {
                    let fromIcon = "fa-check-circle";
                    let toIcon = "fa-times-circle";
                    if (questionType === "multiple_choice") {
                        fromIcon = "fa-check-square";
                        toIcon = "fa-times-rectangle"; // fa-times-square doesn't exist in fontawesome 4.7
                    }
                    buttonEl.querySelector(`i.${fromIcon}`)?.classList.replace(fromIcon, toIcon);
                }
            }
        }
    }

    // ERRORS TOOLS
    // -------------------------------------------------------------------------

    showErrors(errors) {
        const errorKeys = Object.keys(errors || {});
        for (const key of errorKeys) {
            this.el.querySelector(`[id="${key}"] > .o_survey_question_error`).replaceChildren();
        }
        for (const key of errorKeys) {
            const errorEl = this.el.querySelector(`[id="${key}"] > .o_survey_question_error`);
            const textEl = document.createElement("span");
            textEl.textContent = errors[key];
            this.insert(textEl, errorEl);
            errorEl.classList.add("slide_in");
            if (errorKeys[0] === key) {
                scrollTo(this.el.querySelector(`.js_question-wrapper[id="${key}"]`), {
                    behavior: "smooth",
                });
            }
        }
    }

    /**
     * This method is used to scroll to error generated in the backend.
     * (Those errors are displayed when the user skip mandatory question(s))
     */
    scrollToFirstError() {
        const errorEl = this.el.querySelector(".o_survey_question_error :not(:empty)");
        errorEl?.scrollIntoView();
    }

    /**
     * Clean all form errors in order to clean DOM before a new validation
     */
    resetErrors() {
        for (const el of this.el.querySelectorAll(".o_survey_question_error")) {
            el.replaceChildren();
            el.classList.remove("slide_in");
        }
        for (const notificationDestructor of this.notificationDestructors) {
            notificationDestructor();
        }
        this.notificationDestructors = [];
        for (const rowEl of this.el.querySelectorAll(".o_survey_question_matrix th.bg-danger")) {
            rowEl.classList.remove("bg-danger");
        }
    }

    triggerEvent(el, ev) {
        el.dispatchEvent(new Event(ev, { bubbles: true }));
    }

    scrollTop() {
        document.querySelector("#wrapwrap").scrollTo({ top: 0, behavior: "smooth" });
    }

    enableSubmitButtons() {
        for (const submitButtonEl of this.el.querySelectorAll("button[type='submit']")) {
            submitButtonEl.classList.remove("disabled");
        }
    }

    updateNavigationListeners() {
        this.addListener(
            this.surveyNavigationEl.querySelectorAll(".o_survey_navigation_submit"),
            "click",
            this.onSubmit
        );
    }
}

registry.category("public.interactions").add("survey.SurveyForm", SurveyForm);
