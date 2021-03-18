odoo.define('survey.quick.access', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SurveyQuickAccessWidget = publicWidget.Widget.extend({
    selector: '.o_survey_quick_access',
    events: {
        'click button[type="submit"]': '_onSubmit',
        'input #session_code': '_onSessionCodeInput',
    },

        //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

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

            self.$('input').focus();
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    // Handlers
    // -------------------------------------------------------------------------

    _onSessionCodeInput: function () {
        this.el.querySelectorAll('.o_survey_error > span').forEach((elem) => elem.classList.add('d-none'));
    },

    _onKeyPress: function (event) {
        if (event.keyCode === 13) {  // Enter
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
        this.$('.o_survey_error > span').addClass("d-none");
        const sessionCodeInputVal = this.$('input#session_code').val().trim();
        if (!sessionCodeInputVal) {
            self.$('.o_survey_session_error_invalid_code').removeClass("d-none");
            return;
        }
        this._rpc({
            route: `/survey/check_session_code/${sessionCodeInputVal}`,
        }).then(function (response) {
            if (response.survey_url) {
                window.location = response.survey_url;
            } else {
                if (response.error && response.error === 'survey_session_closed') {
                    self.$('.o_survey_session_error_closed').removeClass("d-none");
                } else {
                    self.$('.o_survey_session_error_invalid_code').removeClass("d-none");
                }
            }
        });
    },
});

return publicWidget.registry.SurveyQuickAccessWidget;

});
