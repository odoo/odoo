/** @odoo-module native */
export class DataServiceOptions {
    get databaseTable() {
        const orderIsPurgeable = (order) =>
            Boolean(
                order?.finalized &&
                order.isSynced &&
                order.session_id?.id !== parseInt(odoo.pos_session_id),
            );
        return {
            "pos.order": {
                key: "uuid",
                condition: (record) => orderIsPurgeable(record),
            },
            "pos.order.line": {
                key: "uuid",
                condition: (record) => orderIsPurgeable(record.order_id),
            },
            "pos.payment": {
                key: "uuid",
                condition: (record) => orderIsPurgeable(record.pos_order_id),
            },
            "product.attribute.custom.value": {
                key: "id",
                condition: (record) => orderIsPurgeable(record.order_id),
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
            "decimal.precision": ["name"],
            "product.template": ["pos_categ_ids"],
            "product.product": ["pos_categ_ids", "barcode"],
            "account.fiscal.position": ["tax_ids"],
            "loyalty.program": ["trigger_product_ids"],
            "calendar.event": ["resource_ids"],
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

    get prohibitedAutoLoadedModels() {
        return [
            "pos.order",
            "pos.order.line",
            "pos.session",
            "pos.config",
            "res.users",
            "account.tax",
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
