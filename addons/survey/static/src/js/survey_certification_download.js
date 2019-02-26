odoo.define('survey.certification_download', function (require) {
'use strict';

require('web.dom_ready');

if (!$('.o_survey_download_certification').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_survey_download_certification'");
}

var session = require('web.session');

$('.o_survey_download_certification').click(function (ev) {
    ev.preventDefault();
    var surveyId = $('.o_survey_download_certification').data('surveyId');
    session.get_file({
        url: '/survey/' + surveyId + '/get_certification'
    });
});

});
