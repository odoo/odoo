odoo.define('website_form_project.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website.form_editor_registry');

const _lt = core._lt;

FormEditorRegistry.add('create_task', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: _lt('Task Title'),
    }, {
        type: 'email',
        modelRequired: true,
        fillWith: 'email',
        name: 'email_from',
        string: _lt('Your Email'),
    }, {
        type: 'char',
        name: 'description',
        string: _lt('Description'),
    }],
    fields: [{
        name: 'project_id',
        type: 'many2one',
        relation: 'project.project',
        string: _lt('Project'),
        createAction: 'project.open_view_project_all',
    }],
});

});
