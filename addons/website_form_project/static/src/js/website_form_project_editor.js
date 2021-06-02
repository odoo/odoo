odoo.define('website_form_project.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website_form.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('create_task', {
    defaultTemplateName: 'website_form_project.default_task_form',
    defaultTemplatePath: '/website_form_project/static/src/xml/website_form_project.xml',
    fields: [{
        name: 'project_id',
        type: 'many2one',
        relation: 'project.project',
        required: true,
        string: _t('Project'),
    }],
});

});
