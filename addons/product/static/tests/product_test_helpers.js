import { defineModels } from '@web/../tests/web_test_helpers';
import { ProductProduct } from './mock_server/mock_models/product_product';
import { ProductTemplate } from './mock_server/mock_models/product_template';
import { UomUom } from './mock_server/mock_models/uom_uom';


export const productModels = {
    ProductProduct,
    ProductTemplate,
    UomUom,
};

export function defineProductModels() {
    defineModels(productModels);
}
