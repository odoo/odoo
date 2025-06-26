import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_service/tour_utils';
import comboConfiguratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import productConfiguratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import tourUtils from '@sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('sale_combo_configurator_preselect_single_unconfigurable_items', {
        url: '/odoo',
        steps: () => [
            ...stepUtils.goToAppSteps('sale.sale_menu_root', "Open the sales app"),
            ...tourUtils.createNewSalesOrder(),
            ...tourUtils.selectCustomer("Test Partner"),
            ...tourUtils.addProduct("Combo product"),
            // Assert that only single unconfigurable items are preselected.
            comboConfiguratorTourUtils.assertSelectedComboItemCount(2),
            comboConfiguratorTourUtils.assertComboItemSelected("Product A"),
            comboConfiguratorTourUtils.assertComboItemSelected("Product C"),
            comboConfiguratorTourUtils.assertConfirmButtonDisabled(),
            // Configure the remaining combos.
            comboConfiguratorTourUtils.selectComboItem("Product B"),
            productConfiguratorTourUtils.selectAttribute("Product B", "Attribute B", "B", 'multi'),
            ...productConfiguratorTourUtils.saveConfigurator(),
            comboConfiguratorTourUtils.selectComboItem("Product D"),
            productConfiguratorTourUtils.setCustomAttribute(
                "Product D", "Attribute D", "Test D"
            ),
            ...productConfiguratorTourUtils.saveConfigurator(),
            comboConfiguratorTourUtils.selectComboItem("Product E1"),
            comboConfiguratorTourUtils.assertConfirmButtonEnabled(),
            ...comboConfiguratorTourUtils.saveConfigurator(),
            // Don't end the tour with a form in edition mode.
            ...stepUtils.saveForm(),
        ],
    });
