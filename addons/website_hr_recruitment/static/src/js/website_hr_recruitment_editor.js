odoo.define('website_hr_recruitment.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website.form_editor_registry');

const _lt = core._lt;

FormEditorRegistry.add('apply_job', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'partner_name',
        fillWith: 'name',
        string: _lt('Your Name'),
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email_from',
        string: _lt('Your Email'),
    }, {
        type: 'char',
        required: true,
        fillWith: 'phone',
        name: 'partner_phone',
        string: _lt('Phone Number'),
    }, {
        type: 'text',
        name: 'description',
        string: _lt('Short Introduction'),
    }, {
        type: 'binary',
        custom: true,
        name: 'Resume',
    }],
    fields: [{
        name: 'job_id',
        type: 'many2one',
        relation: 'hr.job',
        string: _lt('Applied Job'),
    }, {
        name: 'department_id',
        type: 'many2one',
        relation: 'hr.department',
        string: _lt('Department'),
    }],
    successPage: '/job-thank-you',
});

});
