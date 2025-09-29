import { models, fields } from '@web/../tests/web_test_helpers';

export class Product extends models.Model {
    _name = 'product';
    _records = [
        {id: 1, name: "Black chair", type: 'goods', list_price: 50.0},
        {id: 2, name: "Blue chair", type: 'goods', list_price: 60.0},
        {id: 3, name: "Black table", type: 'goods', list_price: 70.0},
        {id: 4, name: "Blue table", type: 'goods', list_price: 80.0},
        { id: 5, name: "Test Combo", type: 'combo', combo_ids: [1, 2] },
    ]

    name = fields.Char();
    type = fields.Char();
    list_price = fields.Float();
    combo_ids = fields.Many2many({ relation: 'product.combo' });
}

export class ProductComboItem extends models.Model {
    _name = 'product.combo.item';

    _records = [
        { id: 1, product_id: 1 },
        { id: 2, product_id: 2 },
        { id: 3, product_id: 3 },
        { id: 4, product_id: 4 },
    ]
    combo_id = fields.Many2one({ relation: 'product.combo' });
    product_id = fields.Many2one({ relation: 'product' });
}

export class ProductCombo extends models.Model {
    _name = 'product.combo';

    _records = [
        {id: 1, name: "Chair combo", list_price: 20.0, combo_item_ids: [1, 2]},
        {id: 2, name: "Table combo", list_price: 50.0, combo_item_ids: [3, 4]},
    ];

    name = fields.Char();
    list_price = fields.Float();
    combo_item_ids = fields.One2many({ relation: 'product.combo.item' });
}
