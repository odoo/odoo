import { registry } from '@web/core/registry';
import { stepUtils } from '@web_tour/tour_utils';
import productConfiguratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import { showProductColumn } from "@account/js/tours/tour_utils";
import * as tourUtils from '@sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('sale_order_keep_uom_on_variant_wizard_quantity_change', {
    steps: () => [
        ...showProductColumn('product_template_id'),
        ...tourUtils.editLineMatching("Sofa"),
        tourUtils.editConfiguration(),
        productConfiguratorTourUtils.increaseProductQuantity("Sofa"),
        ...productConfiguratorTourUtils.saveConfigurator(),
        ...stepUtils.saveForm(),
    ],
});
