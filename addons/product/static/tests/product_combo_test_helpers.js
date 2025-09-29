import { defineModels } from '@web/../tests/web_test_helpers';
import {
    ProductCombo,
    ProductComboItem,
    Product,
} from './mock_server/mock_models/product_combo';

export const comboModels = {
    ProductCombo,
    ProductComboItem,
    Product
}

export function defineComboModels() {
    defineModels([ ProductCombo, ProductComboItem, Product ]);
}
