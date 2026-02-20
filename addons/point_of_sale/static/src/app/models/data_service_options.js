// This file is just a "static" class to store the options for the DataService class.
// We are now able to override options from others modules
export class DataServiceOptions {
    get databaseTable() {
        return {
            "pos.order": {
                key: "uuid",
<<<<<<< 56d9c31ec2242aa4982e089dbe4bbf6dc4f57164
                condition: (record) =>
                    record.finalized &&
                    typeof record.id === "number" &&
                    record.pos_session_id !== parseInt(odoo.pos_session_id),
||||||| 7ab52c1675b9764d11454c7b5216064bec4628f8
                condition: (record) => record.finalized && typeof record.id === "number",
=======
                condition: (record) => record.canBeRemovedFromIndexedDB,
>>>>>>> 906ca83dda1b4f75f4a17af8493c8477d1166fb3
            },
            "pos.order.line": {
                key: "uuid",
                condition: (record) => record.order_id?.canBeRemovedFromIndexedDB,
            },
            "pos.payment": {
                key: "uuid",
                condition: (record) => record.pos_order_id?.canBeRemovedFromIndexedDB,
            },
            "product.attribute.custom.value": {
                key: "id",
                condition: (record) =>
                    record.order_id?.finalized && typeof record.order_id.id === "number",
                getRecordsBasedOnLines: (orderlines) =>
                    orderlines.flatMap((line) => line.custom_attribute_value_ids),
            },
        };
    }

    get dynamicModels() {
        return [
            "pos.order",
            "pos.order.line",
            "pos.payment",
            "pos.pack.operation.lot",
            "product.attribute.custom.value",
        ];
    }

    get databaseIndex() {
        const databaseTable = this.databaseTable;
        const indexes = {
            "pos.order": ["uuid"],
            "pos.order.line": ["uuid"],
            "pos.payment": ["uuid"],
            "product.template": ["pos_categ_ids", "write_date"],
            "product.product": ["pos_categ_ids", "barcode"],
            "account.fiscal.position": ["tax_ids"],
            "loyalty.program": ["trigger_product_ids"],
            "calendar.event": ["appointment_resource_ids"],
            "res.partner": ["barcode"],
            "product.uom": ["barcode"],
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
            "pos.order", // Cannot be auto-loaded can cause infinite loop
            "pos.order.line", // Cannot be auto-loaded can cause infinite loop
            "pos.session",
            "pos.config",
            "res.users",
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

    get uniqueModels() {
        return ["pos.session", "res.users", "res.company"];
    }

    get cleanupModels() {
        return ["product.template", "product.product"];
    }

    get prohibitedAutoLoadedFields() {
        return {
            "res.partner": ["property_product_pricelist"],
        };
    }
}
