import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_service/tour_utils';
import configuratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import tourUtils from '@sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('sale_subscription_combo_configurator', {
        url: '/odoo',
        steps: () => [
            ...stepUtils.goToAppSteps('sale_subscription.menu_sale_subscription_root', "Open the subscription app"),
            {
                content: "Create a new SO",
                trigger: '.o_list_button_add',
                run: 'click',
            },
            ...tourUtils.selectCustomer("Test Partner"),
            ...tourUtils.addProduct("Combo product"),
            // Assert that the default subscription price and plan are correct.
            configuratorTourUtils.assertPrice('5.00'),
            configuratorTourUtils.assertPriceInfo("per week"),
            {
                content: "Cancel the configurator",
                trigger: 'button:contains(Cancel)',
                run: 'click',
            },
            {
                content: "Select another subscription plan",
                trigger: 'input#plan_id_0',
                run: 'edit 2 Months',
            },
            {
                trigger: 'ul.ui-autocomplete a:contains("2 Months")',
                run: 'click',
            },
            ...tourUtils.addProduct("Combo product"),
            // Assert that the selected subscription price and plan is correct.
            configuratorTourUtils.assertPrice('15.00'),
            configuratorTourUtils.assertPriceInfo("per 2 months"),
            configuratorTourUtils.selectComboItem("Test Product"),
            ...configuratorTourUtils.saveConfigurator(),
            // Don't end the tour with a form in edition mode.
            ...stepUtils.saveForm(),
        ],
   });
