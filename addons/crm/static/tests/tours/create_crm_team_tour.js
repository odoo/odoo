/** @odoo-module */

import tour from 'web_tour.tour';

tour.register('create_crm_team_tour', {
    url: "/web",
    test: true,
}, [
    ...tour.stepUtils.goToAppSteps('crm.crm_menu_root'),
{
    trigger: 'button[data-menu-xmlid="crm.crm_menu_config"]',
}, {
    trigger: 'a[data-menu-xmlid="crm.crm_team_config"]',
}, {
    trigger: 'button.o_list_button_add',
}, {
    trigger: 'input[id="name"]',
    run: 'text My CRM Team',
}, {
    trigger: 'button.o-kanban-button-new',
}, {
    trigger: 'div.modal-dialog tr:contains("Test Salesman") input.form-check-input',
    run: 'click',
}, {
    trigger: 'div.modal-dialog tr:contains("Test Sales Manager") input.form-check-input',
    run: 'click',
}, {
    trigger: 'div.modal-dialog tr:contains("Test Sales Manager") input.form-check-input:checked',
    run: () => {},
}, {
    trigger: 'button.o_select_button',
}, 
    ...tour.stepUtils.saveForm()
]);
