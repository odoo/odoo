import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_service/tour_utils';
import configuratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import tourUtils from '@sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('sale_renting_combo_configurator', {
        url: '/odoo',
        steps: () => [
            ...stepUtils.goToAppSteps('sale_renting.rental_menu_root', "Open the rental app"),
            {
                content: "Create a new SO",
                trigger: '.o-kanban-button-new',
                run: 'click',
            },
            ...tourUtils.selectCustomer("Test Partner"),
            ...tourUtils.addProduct("Combo product"),
            // Assert that the rental price and duration are correct.
            configuratorTourUtils.assertPrice('15.00'),
            configuratorTourUtils.assertPriceInfo("1 Day"),
            configuratorTourUtils.selectComboItem("Test Product"),
            ...configuratorTourUtils.saveConfigurator(),
            // Don't end the tour with a form in edition mode.
            ...stepUtils.saveForm(),
        ],
   });
