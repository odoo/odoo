odoo.define('website_crm.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('create_lead', {
    formFields: [{
        type: 'char',
        required: true,
        name: 'contact_name',
        fillWith: 'name',
        string: 'Your Name',
    }, {
        type: 'tel',
        name: 'phone',
        fillWith: 'phone',
        string: 'Phone Number',
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email_from',
        string: 'Your Email',
    }, {
        type: 'char',
        required: true,
        fillWith: 'commercial_company_name',
        name: 'partner_name',
        string: 'Your Company',
    }, {
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: 'Subject',
    }, {
        type: 'text',
        required: true,
        name: 'description',
        string: 'Your Question',
    }],
    fields: [{
        name: 'team_id',
        type: 'many2one',
        relation: 'crm.team',
        domain: [['use_opportunities', '=', true]],
        string: _t('Sales Team'),
        title: _t('Assign leads/opportunities to a sales team.'),
    }, {
        name: 'user_id',
        type: 'many2one',
        relation: 'res.users',
        domain: [['share', '=', false]],
        string: _t('Salesperson'),
        title: _t('Assign leads/opportunities to a salesperson.'),
    }],
});

});
