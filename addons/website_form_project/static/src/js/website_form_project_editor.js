/** @odoo-module **/

import core from "web.core";
import FormEditorRegistry from "website.form_editor_registry";

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
        fillWith: 'email',
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
        string: _t('Project'),
        createAction: 'project.open_view_project_all',
    }],
});
