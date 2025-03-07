export const MODEL_DEF = {
    "pos.table": {
        name: { name: "name", type: "char" },
    },
    "pos.order": {
        id: { type: "integer", compute: false, related: false },
        lines: {
            name: "lines",
            model: "pos.order",
            relation: "pos.order.line",
            type: "one2many",
            inverse_name: "order_id",
        },

        total: {
            name: "total",
            type: "float",
        },

        table_id: {
            name: "table_id",
            model: "pos.order",
            relation: "pos.table",
            type: "many2one",
        },

        date: {
            type: "datetime",
        },

        uuid: { name: "uuid", type: "char" },
    },
    "pos.order.line": {
        order_id: {
            name: "order_id",
            model: "pos.order.line",
            relation: "pos.order",
            type: "many2one",
            ondelete: "cascade",
        },
        name: { name: "name", type: "char" },
        quantity: {
            name: "quantity",
            type: "float",
        },
        attribute_ids: {
            type: "many2many",
            relation: "product.attribute",
            relation_table: "order_line_product_attributes_rel",
        },
        uuid: { name: "uuid", type: "char" },
    },
    "product.attribute": {
        name: { type: "char" },
    },
};
export const MODEL_OPTS = {
    dynamicModels: ["pos.order", "pos.order.line"],
    databaseIndex: {
        "pos.order": ["uuid"],
        "pos.order.line": ["uuid"],
    },
    databaseTable: {
        "pos.order": { key: "uuid" },
        "pos.order.line": { key: "uuid" },
    },
};
