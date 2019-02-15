odoo.define('website_slides_survey.certification_download', function (require) {
'use strict';

var WebsiteSlides = require('website_slides.slides');
var session = require('web.session');

WebsiteSlides.include({
    events: _.extend({}, WebsiteSlides.prototype.events, {
        'click .o_wslides_survey_download_certification': '_onDownloadCertificationClick'
    }),

    /**
     * @private
     */
    _onDownloadCertificationClick: function () {
        var surveyId = this.$('.o_wslides_survey_download_certification').data('survey_id');
        session.get_file({
            url: '/survey/' + surveyId + '/get_certification'
        });
    }
});

});
