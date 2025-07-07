import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('create_crm_team_tour', {
    url: "/odoo",
    steps: () => [
    ...stepUtils.goToAppSteps('crm.crm_menu_root'),
{
    trigger: 'button[data-menu-xmlid="crm.crm_menu_config"]',
    run: "click",
}, {
    trigger: 'a[data-menu-xmlid="crm.crm_team_config"]',
    run: "click",
}, {
    trigger: 'button.o_list_button_add',
    run: "click",
}, {
    trigger: 'input[id="name_0"]',
    run: "edit My CRM Team",
}, {
    trigger: '.btn.o-kanban-button-new',
    run: "click",
}, {
    trigger: 'div.modal-dialog tr:contains("Test Salesman") input.form-check-input',
    run: 'click',
}, {
    trigger: 'div.modal-dialog tr:contains("Test Sales Manager") input.form-check-input',
    run: 'click',
}, {
    trigger: 'div.modal-dialog tr:contains("Test Sales Manager") input.form-check-input:checked',
}, {
    trigger: '.o_selection_box:contains(2)',
}, {
    trigger: 'button.o_select_button',
    run: "click",
},
    ...stepUtils.saveForm()
]});
