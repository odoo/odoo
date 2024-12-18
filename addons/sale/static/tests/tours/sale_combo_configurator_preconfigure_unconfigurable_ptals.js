import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_service/tour_utils';
import comboConfiguratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import productConfiguratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import tourUtils from '@sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('sale_combo_configurator_preconfigure_unconfigurable_ptals', {
        url: '/odoo',
        steps: () => [
            ...stepUtils.goToAppSteps('sale.sale_menu_root', "Open the sales app"),
            ...tourUtils.createNewSalesOrder(),
            ...tourUtils.selectCustomer("Test Partner"),
            ...tourUtils.addProduct("Combo product"),
            {
                content: "Verify that unconfigurable ptals are preconfigured",
                trigger: `${comboConfiguratorTourUtils.comboItemSelector("Test product")}:contains("Attribute A: A")`,
            },
            {
                content: "Verify that configurable ptals aren't preconfigured",
                trigger: `${comboConfiguratorTourUtils.comboItemSelector("Test product")}:not(:contains("Attribute B: B"))`,
            },
            comboConfiguratorTourUtils.selectComboItem("Test product"),
            productConfiguratorTourUtils.selectAttribute(
                "Test product", "Attribute B", "B", 'multi'
            ),
            ...productConfiguratorTourUtils.saveConfigurator(),
            {
                content: "Verify that configurable ptals are now configured",
                trigger: `${comboConfiguratorTourUtils.comboItemSelector("Test product")}:contains("Attribute B: B")`,
            },
            ...comboConfiguratorTourUtils.saveConfigurator(),
            // Don't end the tour with a form in edition mode.
            ...stepUtils.saveForm(),
        ],
    });
