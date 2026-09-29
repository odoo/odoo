import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';

registry.category("builder.form_editor_actions").add('create_lead', {
    fields: [{
        name: 'team_id',
        type: 'many2one',
        relation: 'crm.team',
        domain: [['use_opportunities', '=', true]],
        string: _t('Sales Team'),
        title: _t('Assign leads/opportunities to a sales team.'),
        dialogTitle: _t("Create a Sales Team"),
        dialogDescription: _t(
            "Your current changes will be saved, and you'll be redirected to the CRM app"
        ),
        createAction: "sales_team.crm_team_action_config",
    }, {
        name: 'user_id',
        type: 'many2one',
        relation: 'res.users',
        domain: [['share', '=', false]],
        string: _t('Salesperson'),
        title: _t('Assign leads/opportunities to a salesperson.'),
    }],
});
