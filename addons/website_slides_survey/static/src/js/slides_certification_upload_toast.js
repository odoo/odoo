odoo.define('website_slides.certification_upload_toast', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

var sessionStorage = window.sessionStorage;
var core = require('web.core');
var _t = core._t;


publicWidget.registry.CertificationUploadToast = publicWidget.Widget.extend({
    selector: '.o_certification_upload_toast',
    
    /**
     * @private
     */
    start: function () {
        var self = this;
        this._super.apply(this, arguments).then(function () {
            var url = sessionStorage.getItem("certification_toast");
            if (url) {
                var message = _.str.sprintf(_t('Follow this link to add questions to your certification. <a href="%s">Edit certification</a>'), url);
                self.displayNotification({
                    type: 'info',
                    title: _t('Certification created'),
                    message: message,
                    sticky: false
            });
            sessionStorage.removeItem("certification_toast");
        }
        });
    },
});
});
