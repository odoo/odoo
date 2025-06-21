/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('create_crm_team_tour', {
    url: "/web",
    test: true,
    steps: () => [
    ...stepUtils.goToAppSteps('crm.crm_menu_root'),
{
    trigger: 'button[data-menu-xmlid="crm.crm_menu_config"]',
}, {
    trigger: 'a[data-menu-xmlid="crm.crm_team_config"]',
}, {
    trigger: 'button.o_list_button_add',
}, {
    trigger: 'input[id="name_0"]',
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
    trigger: '.o_list_selection_box:contains(2)',
    run: () => {},
}, {
    trigger: 'button.o_select_button',
}, 
    ...stepUtils.saveForm()
]});
