odoo.define('website_hr_recruitment.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website_form.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('apply_job', {
    formFields: [{
        type: 'char',
        modelRequired: true,
        name: 'partner_name',
        string: 'Your Name',
    }, {
        type: 'email',
        required: true,
        name: 'email_from',
        string: 'Your Email',
    }, {
        type: 'char',
        required: true,
        name: 'partner_phone',
        string: 'Phone Number',
    }, {
        type: 'text',
        name: 'description',
        string: 'Short Introduction',
    }, {
        type: 'binary',
        custom: true,
        name: 'Resume',
    }],
    fields: [{
        name: 'job_id',
        type: 'many2one',
        relation: 'hr.job',
        string: _t('Applied Job'),
    }, {
        name: 'department_id',
        type: 'many2one',
        relation: 'hr.department',
        string: _t('Department'),
    }],
    successPage: '/job-thank-you',
});

});
