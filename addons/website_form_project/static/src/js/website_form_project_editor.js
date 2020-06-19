odoo.define('website_form_project.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website_form.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('create_task', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: 'Task Title',
    }, {
        type: 'email',
        modelRequired: true,
        name: 'email_from',
        string: 'Your Email',
    }, {
        type: 'char',
        name: 'description',
        string: 'Description',
    }],
    fields: [{
        name: 'project_id',
        type: 'many2one',
        relation: 'project.project',
        required: true,
        string: _t('Project'),
    }],
});

});
