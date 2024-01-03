/** @odoo-module */

// This file is just a "static" class to store the options for the DataService class.
// We are now able to override options from others modules
export class DataServiceOptions {
    get databaseTable() {
        return [
            { name: "pos.order", key: "uuid", condition: (record) => record.finalized },
            {
                name: "pos.order.line",
                key: "uuid",
                condition: (record) => record.order_id?.finalized,
            },
            {
                name: "pos.payment",
                key: "uuid",
                condition: (record) => record.pos_order_id?.finalized,
            },
            {
                name: "pos.pack.operation.lot",
                key: "id",
                condition: (record) => record.pos_order_line_id?.order_id?.finalized,
            },
            {
                name: "product.product",
                key: "id",
                condition: (record) => {
                    return record.models["pos.order.line"].find(
                        (l) => l.product_id?.id === record.id
                    );
                },
            },
        ];
    }

    get databaseIndex() {
        return {
            "pos.order": ["uuid"],
            "product.product": ["barcode", "pos_categ_ids", "write_date"],
            "account.fiscal.position": ["tax_ids"],
            "account.fiscal.position.tax": ["tax_src_id"],
            "product.packaging": ["barcode"],
            "loyalty.program": ["trigger_product_ids"],
            "calendar.event": ["appointment_resource_ids"],
        };
    }

    get autoLoadedOrmMethods() {
        return ["read", "search_read", "create"];
    }

    get pohibitedAutoLoadedModels() {
        return [
            "pos.session",
            "pos.config",
            "res.users",
            "pos.order",
            "account.tax", // Cannot be auto-loaded because the record needs adaptions
            "account.fiscal.postion", // Cannot be auto-loaded because the record needs adaptions
        ];
    }

    get cascadeDeleteModels() {
        return [
            "pos.order",
            "pos.order.line",
            "pos.payment",
            "product.attribute.custom.value",
            "pos.pack.operation.lot",
        ];
    }
}
