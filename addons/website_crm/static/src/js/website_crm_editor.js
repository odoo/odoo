import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

registry.category("website.form_editor_actions").add('create_lead', {
    formFields: [{
        type: 'char',
        required: true,
        name: 'contact_name',
        fillWith: 'name',
        string: _t('Your Name'),
    }, {
        type: 'tel',
        name: 'phone',
        fillWith: 'phone',
        string: _t('Phone Number'),
    }, {
        type: 'email',
        required: true,
        fillWith: 'email',
        name: 'email_from',
        string: _t('Your Email'),
    }, {
        type: 'char',
        required: true,
        fillWith: 'commercial_company_name',
        name: 'partner_name',
        string: _t('Your Company'),
    }, {
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: _t('Subject'),
    }, {
        type: 'text',
        required: true,
        name: 'description',
        string: _t('Your Question'),
    }],
    fields: [{
        name: 'team_id',
        type: 'many2one',
        relation: 'crm.team',
        searchable: true,
        dialogTitle: _t('Create a Sales Team'),
        dialogDescription: _t("Your current changes will be saved and you'll be redirected to the CRM app"),
        domain: [["use_opportunities", "=", true], ["active", "=", true]],
        string: _t('Sales Team'),
        title: _t('Assign leads/opportunities to a sales team.'),
        createAction: "sales_team.crm_team_action_config",
    }, {
        name: 'user_id',
        type: 'many2one',
        relation: 'res.users',
        searchable: true,
        domain: [['share', '=', false], ["active", "=", true]],
        string: _t('Salesperson'),
        title: _t('Assign leads/opportunities to a salesperson.'),
    }],
});
