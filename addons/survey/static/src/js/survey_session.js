odoo.define('survey.user_session', function (require) {
'use strict';

require('bus.BusService');
var publicWidget = require('web.public.widget');

publicWidget.registry.SurveySession = publicWidget.Widget.extend({
    selector: '.o_survey_session',

    start: function () {
        var self = this;

        this._super.apply(this, arguments).then(function () {
            var surveySessionUuid = self.$el.data('surveySessionUuid');
            if (surveySessionUuid) {
                self.surveySessionUuid = surveySessionUuid;
                self.call('bus_service', 'addChannel', surveySessionUuid);
                self.call('bus_service', 'startPolling');

                self.call('bus_service', 'onNotification', self, self._onNotification);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Array[]} notifications
     */
    _onNotification: function (notifications) {
        if (notifications && notifications.length !== 0) {
            notifications.forEach(function (notification) {
                if (notification.length >= 2) {
                    var event = notification[1];
                    if (event.type === 'next_question' ||
                        event.type === 'end_session') {
                        document.location.reload();
                    }
                }
            });
        }
    }
});

return publicWidget.registry.SurveySession;

});
