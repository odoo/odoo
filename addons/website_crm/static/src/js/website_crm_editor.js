odoo.define('website_crm.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website_form.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('create_lead', {
    defaultTemplateName: 'website_crm.default_crm_form',
    defaultTemplatePath: '/website_crm/static/src/xml/website_crm.xml',
    fields: [{
        name: 'team_id',
        type: 'many2one',
        relation: 'crm.team',
        domain: [['use_opportunities', '=', true]],
        string: _t('Sales Channel'),
        title: _t('Assign leads/opportunities to a sales channel.'),
    }, {
        name: 'user_id',
        type: 'many2one',
        relation: 'res.users',
        string: _t('Salesperson'),
        title: _t('Assign leads/opportunities to a salesperson.'),
    }],
});

});
