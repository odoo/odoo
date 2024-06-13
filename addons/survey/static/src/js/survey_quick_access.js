/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.SurveyQuickAccessWidget = publicWidget.Widget.extend({
    selector: '.o_survey_quick_access',
    events: {
        'click button[type="submit"]': '_onSubmit',
        'input #session_code': '_onSessionCodeInput',
        'click .o_survey_launch_session': '_onLaunchSessionClick',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },
    
    /**
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // Init event listener
            if (!self.readonly) {
                $(document).on('keypress', self._onKeyPress.bind(self));
            }
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    // Handlers
    // -------------------------------------------------------------------------

    _onLaunchSessionClick: async function () {
        const sessionResult = await this.orm.call(
            "survey.survey",
            "action_start_session",
            [[this.$(".o_survey_launch_session").data("surveyId")]]
        );
        window.location = sessionResult.url;
    },

    _onSessionCodeInput: function () {
        this.el.querySelectorAll('.o_survey_error > span').forEach((elem) => elem.classList.add('d-none'));
        this.$('.o_survey_launch_session').addClass('d-none');
        this.$('button[type="submit"]').removeClass('d-none');
    },

    _onKeyPress: function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            this._submitCode();
        }
    },

    _onSubmit: function (event) {
        event.preventDefault();
        this._submitCode();
    },

    _submitCode: function () {
        var self = this;
        this.$('.o_survey_error > span').addClass('d-none');
        const sessionCodeInputVal = this.$('input#session_code').val().trim();
        if (!sessionCodeInputVal) {
            self.$('.o_survey_session_error_invalid_code').removeClass('d-none');
            return;
        }
        rpc(`/survey/check_session_code/${sessionCodeInputVal}`).then(function (response) {
            if (response.survey_url) {
                window.location = response.survey_url;
            } else {
                if (response.error && response.error === 'survey_session_not_launched') {
                    self.$('.o_survey_session_error_not_launched').removeClass('d-none');
                    if ("survey_id" in response) {
                        self.$('button[type="submit"]').addClass('d-none');
                        self.$('.o_survey_launch_session').removeClass('d-none');
                        self.$('.o_survey_launch_session').data('surveyId', response.survey_id);
                    }
                } else {
                    self.$('.o_survey_session_error_invalid_code').removeClass('d-none');
                }
            }
        });
    },
});

export default publicWidget.registry.SurveyQuickAccessWidget;
