odoo.define('website_slides_survey.certification_upload_toast', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var {Markup, sprintf} = require('web.utils');

var sessionStorage = window.sessionStorage;
var core = require('web.core');
var _t = core._t;


publicWidget.registry.CertificationUploadToast = publicWidget.Widget.extend({
    selector: '.o_wslides_survey_certification_upload_toast',

    /**
     * @override
     */
    start: function () {
        var self = this;
        this._super.apply(this, arguments).then(function () {
            var url = sessionStorage.getItem("survey_certification_url");
            if (url) {
                var message = sprintf(Markup(
                    _t('Follow this link to add questions to your certification. <a href="%s">Edit certification</a>')), url);
                self.displayNotification({
                    type: 'info',
                    title: _t('Certification created'),
                    message: message,
                    sticky: true,
                });
                sessionStorage.removeItem("survey_certification_url");
            }
        });
    },
});

return publicWidget.registry.CertificationUploadToast;

});
