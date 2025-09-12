import { defineModels } from '@web/../tests/web_test_helpers';
import {
    ProductCombo,
    ProductComboItem,
    ProductProduct,
} from './mock_server/mock_models/product_combo';

export const comboModels = {
    ProductCombo,
    ProductComboItem,
    ProductProduct,
}

export function defineComboModels() {
    defineModels(comboModels);
}
