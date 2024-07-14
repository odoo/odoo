/** @odoo-module **/

import { addFakeModel, addModelNamesToFetch } from '@bus/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch(['res.groups', 'ir.ui.view']);
addFakeModel('product', {
    partner_ids: { string: "Attachments", type: "one2many", relation: "partner" },
    coucou_id: { string: "coucou", type: "many2one", relation: "coucou" },
    display_name: { string: "Display Name", type: "char" },
    m2m: { string: "M2M", type: "many2many", relation: "product" },
    m2o: { string: "M2O", type: "many2one", relation: 'partner' },
    related: { type: "char", related: "partner.display_name", string: "myRelatedField" },
    sign: { string: "Signature", type: "binary" },
    toughness: { manual: true, string: "toughness", type: 'selection', selection: [['0', "Hard"], ['1', "Harder"]] },
});
addFakeModel('coucou', {
    display_name: { string: "Display Name", type: "char" },
    char_field: { string: "A char", type: "char" },
    croissant: { string: "Croissant", type: "integer" },
    m2o: { string: "M2O", type: "many2one", relation: 'product' },
    message_attachment_count: { string: 'Attachment count', type: 'integer' },
    priority: { string: "Priority", type: "selection", manual: true, selection: [['1', "Low"], ['2', "Medium"], ['3', "High"]] },
    product_ids: { string: "Products", type: "one2many", relation: "product" },
    start: { string: "Start Date", type: 'datetime' },
    stop: { string: "Stop Date", type: 'datetime' },
});
addFakeModel('partner', {
    display_name: { string: "Display Name", type: "char" },
    image: { string: "Image", type: "binary" },
    displayed_image_id: { string: "cover", type: "many2one", relation: "ir.attachment" },
});
