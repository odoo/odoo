import { models } from '@web/../tests/web_test_helpers';
import { ProductProduct as ProductModel } from './product_product';

export class ProductProduct extends ProductModel {
    _records = [
        { id: 1, name: "Black chair", type: 'goods', list_price: 50.0 },
        { id: 2, name: "Blue chair", type: 'goods', list_price: 60.0 },
        { id: 3, name: "Black table", type: 'goods', list_price: 70.0 },
        { id: 4, name: "Blue table", type: 'goods', list_price: 80.0 },
        { id: 5, name: "Test Combo", type: 'combo', combo_ids: [1, 2] },
    ];
}

export class ProductComboItem extends models.ServerModel {
    _name = 'product.combo.item';
    _records = [
        { id: 1, product_id: 1 },
        { id: 2, product_id: 2 },
        { id: 3, product_id: 3 },
        { id: 4, product_id: 4 },
    ];
}

export class ProductCombo extends models.ServerModel {
    _name = 'product.combo';
    _records = [
        { id: 1, name: "Chair combo", combo_item_ids: [1, 2] },
        { id: 2, name: "Table combo", combo_item_ids: [3, 4] },
    ];
}
