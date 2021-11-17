odoo.define('survey.SurveyFormView', function (require) {
'use strict';

const SurveyFormController = require('survey.SurveyFormController');
const FormRenderer = require('web.FormRenderer');
const FormView = require('web.FormView');
const viewRegistry = require('web.view_registry');

const SurveyFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: SurveyFormController,
        Renderer: FormRenderer,
    }),
});

viewRegistry.add('survey_survey_form', SurveyFormView);

return SurveyFormView;

});