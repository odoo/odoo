// This file is just a "static" class to store the options for the DataService class.
// We are now able to override options from others modules
export class DataServiceOptions {
    get databaseTable() {
        return {
            "pos.order": {
                key: "uuid",
                condition: (record) => record.finalized && typeof record.id === "number",
            },
            "pos.order.line": {
                key: "uuid",
                condition: (record) =>
                    record.order_id?.finalized && typeof record.order_id.id === "number",
            },
            "pos.payment": {
                key: "uuid",
                condition: (record) =>
                    record.pos_order_id?.finalized && typeof record.pos_order_id.id === "number",
            },
            "pos.pack.operation.lot": {
                key: "id",
                condition: (record) =>
                    record.pos_order_line_id?.order_id?.finalized &&
                    typeof record.pos_order_line_id.order_id.id === "number",
            },
            "product.attribute.custom.value": {
                key: "id",
                condition: (record) => {
                    return record.models["pos.order.line"].find((l) => {
                        const customAttrIds = l.custom_attribute_value_ids.map((v) => v.id);
                        return customAttrIds.includes(record.id);
                    });
                },
            },
        };
    }

    get databaseIndex() {
        const databaseTable = this.databaseTable;
        const indexes = {
            "pos.order": ["uuid"],
            "pos.order.line": ["uuid"],
            "product.product": ["barcode", "pos_categ_ids", "write_date"],
            "account.fiscal.position": ["tax_ids"],
            "product.packaging": ["barcode"],
            "pos.payment": ["uuid"],
            "loyalty.program": ["trigger_product_ids"],
            "calendar.event": ["appointment_resource_ids"],
            "res.partner": ["barcode"],
        };

        for (const model in databaseTable) {
            if (!indexes[model]) {
                indexes[model] = [databaseTable[model].key];
            } else if (!indexes[model].includes(databaseTable[model].key)) {
                indexes[model].push(databaseTable[model].key);
            }
        }

        return indexes;
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
        ];
    }

    get cascadeDeleteModels() {
        return [
            "pos.order.line",
            "pos.payment",
            "product.attribute.custom.value",
            "pos.pack.operation.lot",
        ];
    }
}
