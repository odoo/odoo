odoo.define('survey.main', function(require) {
'use strict';

require('web.dom_ready');

var base = require('web_editor.base');
var SurveyFormWidget = require('survey.form.widget');

base.ready().then(function () {
    $('.o_survey_form').each(function () {
        var $elem = $(this);
        var widget = new SurveyFormWidget(null, $elem.data());
        widget.attachTo($elem);
    });
});

return {
};

});