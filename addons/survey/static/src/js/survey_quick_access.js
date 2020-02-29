odoo.define('survey.quick.access', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SurveyQuickAccessWidget = publicWidget.Widget.extend({
    selector: '.o_survey_quick_access',
    events: {
        'click button[type="submit"]': '_onSubmit',
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
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    // Handlers
    // -------------------------------------------------------------------------

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
        this.$('.o_survey_error').addClass("d-none");
        var $accessCodeInput = this.$('input#access_code');
        this._rpc({
            route: `/survey/check_access_code/${$accessCodeInput.val()}`,
        }).then(function (response) {
            if (response.survey_url) {
                window.location = response.survey_url;
            } else {
                self.$('.o_survey_error').removeClass("d-none");
            }
        });
    },
});

return publicWidget.registry.SurveyQuickAccessWidget;

});
