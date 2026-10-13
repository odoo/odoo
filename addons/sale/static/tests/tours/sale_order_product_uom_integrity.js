import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_utils';
import productConfiguratorTourUtils from '@sale/tours/product_configurator_tour_utils';
import * as tourUtils from '@sale/tours/tour_utils';

registry.category('web_tour.tours').add('sale_order_keep_uom_on_variant_wizard_quantity_change', {
    steps: () => [
        tourUtils.editConfiguration("Sofa"),
        productConfiguratorTourUtils.increaseProductQuantity("Sofa"),
        ...productConfiguratorTourUtils.saveConfigurator(),
        ...stepUtils.saveForm(),
    ],
});
