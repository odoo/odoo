import { defineModels } from '@web/../tests/web_test_helpers';
import { ProductProduct } from './mock_server/mock_models/product_product';
import { ProductTemplate } from './mock_server/mock_models/product_template';


export const productModels = {
    ProductProduct,
    ProductTemplate,
};

export function defineProductModels() {
    defineModels(productModels);
}
