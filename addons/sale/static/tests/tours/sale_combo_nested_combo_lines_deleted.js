import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_service/tour_utils';
import comboConfiguratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import tourUtils from '@sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('sale_combo_nested_combo_lines_deleted', {
        url: '/odoo',
        steps: () => [
            ...stepUtils.goToAppSteps('sale.sale_menu_root', "Open the sales app"),
            ...tourUtils.createNewSalesOrder(),
            ...tourUtils.selectCustomer("Test Partner"),
            ...tourUtils.addProduct("Combo product"),
            comboConfiguratorTourUtils.selectComboItem("Product A1"),
            ...comboConfiguratorTourUtils.saveConfigurator(),
            {
                content: "Click to activate the row containing Product A1",
                trigger: '.o_form_view .o_list_view tbody tr:contains("Product A1") td.o_data_cell',
                run: 'click'
            },
            {
                content: "Edit and replace with Combo Product",
                trigger: '.o_list_view tbody tr td[name="product_template_id"] input',
                run: 'edit Combo Product',
            },
            {
                content: "Select Combo Product from dropdown",
                trigger: '.ui-autocomplete .ui-menu-item:contains("Combo Product")',
                run: 'click',
            },
            comboConfiguratorTourUtils.selectComboItem("Product A1"),
            ...comboConfiguratorTourUtils.saveConfigurator(),
            {
                content: "Click delete on Desk Organizer line",
                trigger: '.o_list_view tbody tr:has(td span:contains("Combo Product")) .o_list_record_remove button[name="delete"]',
                run: 'click',
            },
            ...stepUtils.saveForm(),
        ],
    });
