odoo.define('survey.main', function(require) {
'use strict';

require('web.dom_ready');

var ajax = require('web.ajax');
var SurveyFormWidget = require('survey.form.widget');

function load_locale(){
    var url = '/web/webclient/locale/' + (document.documentElement.getAttribute('lang') || 'en_US').replace('-', '_');
    return ajax.loadJS(url);
}

// datetimepicker use moment locale to display date format according to language
// frontend does not load moment locale at all.
// so wait until DOM ready with locale then init datetimepicker
var ready = $.when(load_locale());

ready.then(function () {
    $('.o_survey_form').each(function () {
        var $elem = $(this);
        var widget = new SurveyFormWidget(null, $elem.data());
        widget.attachTo($elem);
    });
});

return {
};

});
