import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_service/tour_utils';
import comboConfiguratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import productConfiguratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import tourUtils from '@sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('sale_combo_configurator', {
        url: '/odoo',
        steps: () => [
            ...stepUtils.goToAppSteps('sale.sale_menu_root', "Open the sales app"),
            ...tourUtils.createNewSalesOrder(),
            ...tourUtils.selectCustomer("Test Partner"),
            ...tourUtils.addProduct("Combo product"),
            // Assert that the combo configurator has the correct data.
            comboConfiguratorTourUtils.assertComboCount(2),
            comboConfiguratorTourUtils.assertComboItemCount("Combo A", 2),
            comboConfiguratorTourUtils.assertComboItemCount("Combo B", 2),
            // Assert that price changes when the quantity is updated.
            comboConfiguratorTourUtils.assertQuantity(1),
            comboConfiguratorTourUtils.assertPrice('25.00'),
            comboConfiguratorTourUtils.increaseQuantity(),
            comboConfiguratorTourUtils.assertQuantity(2),
            comboConfiguratorTourUtils.assertPrice('50.00'),
            comboConfiguratorTourUtils.decreaseQuantity(),
            comboConfiguratorTourUtils.assertQuantity(1),
            comboConfiguratorTourUtils.assertPrice('25.00'),
            comboConfiguratorTourUtils.setQuantity(3),
            comboConfiguratorTourUtils.assertQuantity(3),
            comboConfiguratorTourUtils.assertPrice('75.00'),
            // Assert that the combo configurator can only be saved after selecting an item for each
            // combo.
            comboConfiguratorTourUtils.assertConfirmButtonDisabled(),
            comboConfiguratorTourUtils.selectComboItem("Product A2"),
            comboConfiguratorTourUtils.selectComboItem("Product B2"),
            comboConfiguratorTourUtils.assertConfirmButtonEnabled(),
            // Assert that the product configurator is opened when a product with `no_variant` PTALs
            // is selected.
            comboConfiguratorTourUtils.selectComboItem("Product A1"),
            productConfiguratorTourUtils.selectAttribute("Product A1", "No variant attribute", "A"),
            {
                content: "Confirm the product configurator",
                trigger: 'button[name="sale_product_configurator_confirm_button"]',
                run: 'click',
            },
            // Assert that the extra price of a combo item is applied correctly.
            comboConfiguratorTourUtils.assertPrice('90.00'),
            // Assert that the extra price of a `no_variant` PTAV is applied correctly.
            comboConfiguratorTourUtils.selectComboItem("Product A1"),
            ...productConfiguratorTourUtils.selectAndSetCustomAttribute(
                "Product A1", "No variant attribute", "B", "Some custom value"
            ),
            {
                content: "Confirm the product configurator",
                trigger: 'button[name="sale_product_configurator_confirm_button"]',
                run: 'click',
            },
            comboConfiguratorTourUtils.assertPrice('93.00'),
            // Assert that the order's content is correct.
            ...comboConfiguratorTourUtils.saveConfigurator(),
            tourUtils.checkSOLDescriptionContains("Combo product x 3"),
            tourUtils.checkSOLDescriptionContains(
                "Product A1", "No variant attribute: B: Some custom value"
            ),
            tourUtils.checkSOLDescriptionContains("Product B2"),
            {
                content: "Verify the combo item quantities",
                trigger: 'td[name="product_uom_qty"]:contains(3.00)',
            },
            {
                content: "Verify the first combo item's unit price",
                trigger: 'td[name="price_unit"]:contains(18.50)',
            },
            {
                content: "Verify the second combo item's unit price",
                trigger: 'td[name="price_unit"]:contains(12.50)',
            },
            {
                content: "Verify the order's total price",
                trigger: 'div.oe_subtotal_footer:contains(93.00)',
            },
            // Assert that the combo configurator is opened with the previous selection when the
            // combo is edited.
            tourUtils.editLineMatching("Combo product x 3"),
            tourUtils.editConfiguration(),
            comboConfiguratorTourUtils.setQuantity(2),
            comboConfiguratorTourUtils.assertComboItemSelected("Product A1"),
            comboConfiguratorTourUtils.assertComboItemSelected("Product B2"),
            comboConfiguratorTourUtils.selectComboItem("Product A2"),
            // Assert that the order's content has been updated.
            ...comboConfiguratorTourUtils.saveConfigurator(),
            tourUtils.checkSOLDescriptionContains("Combo product x 2"),
            tourUtils.checkSOLDescriptionContains("Product A2"),
            tourUtils.checkSOLDescriptionContains("Product B2"),
            {
                content: "Verify the combo item quantities",
                trigger: 'td[name="product_uom_qty"]:contains(2.00)',
            },
            {
                content: "Verify the first combo item's unit price",
                trigger: 'td[name="price_unit"]:contains(12.50)',
            },
            {
                content: "Verify the second combo item's unit price",
                trigger: 'td[name="price_unit"]:contains(12.50)',
            },
            {
                content: "Verify the order's total price",
                trigger: 'div.oe_subtotal_footer:contains(50.00)',
            },
            // Don't end the tour with a form in edition mode.
            ...stepUtils.saveForm(),
        ],
    });
