import { models, Command } from "@web/../tests/web_test_helpers";

export class PosOrder extends models.ServerModel {
    _name = "pos.order";

    get_preparation_change(id) {
        const read = this.read([id]);
        const changes = read[0]?.last_order_preparation_change || "{}";
        return {
            last_order_preparation_change: changes,
        };
    }

    read_pos_orders(domain) {
        const results = this.search(domain, this._load_pos_data_fields(), false);
        return this.read_pos_data(results);
    }

    _load_pos_data_fields() {
        return [];
    }

    action_pos_order_cancel(self) {
        const records = this.browse(self);
        const orderIds = [];

        for (const record of records) {
            this.write([record.id], { state: "cancel" });
            orderIds.push(record.id);
        }

        return {
            "pos.order": this.read(orderIds, this._load_pos_data_fields(), false),
        };
    }

    create() {
        const orderId = super.create(...arguments);
        this.write([orderId], { pos_reference: "000-0-000000" });
        return orderId;
    }

    sync_from_ui(data) {
        const orderIds = [];
        for (const record of data) {
            const record_uuid_mapping = record.relations_uuid_mapping || {};
            delete record.relations_uuid_mapping;
            if (record.id) {
                this.write([record.id], record);
                orderIds.push(record.id);
            } else {
                const id = this.create(record);
                orderIds.push(id);
            }
            for (const [modelName, mapping] of Object.entries(record_uuid_mapping)) {
                // Search for owner records by UUID
                const ownerRecords = this.env[modelName].search_read(
                    [["uuid", "in", Object.keys(mapping)]],
                    ["id", "uuid"]
                );
                for (const [uuid, fields] of Object.entries(mapping)) {
                    for (const [name, uuids] of Object.entries(fields)) {
                        const field = this.env[modelName]._fields[name];
                        if (["one2many", "many2many"].includes(field.type)) {
                            // Get all related records by uuids
                            const relatedRecords = this.env[field.relation].search_read(
                                [["uuid", "in", uuids]],
                                ["id", "uuid"]
                            );
                            const ownerRecord = ownerRecords.find((r) => r.uuid === uuid);
                            if (ownerRecord) {
                                this.env[modelName].write([ownerRecord.id], {
                                    [name]: relatedRecords.map((r) => Command.link(r.id)),
                                });
                            }
                        } else {
                            // single record relation (many2one)
                            const record = this.env[field.relation].search([["uuid", "=", uuids]]);
                            const ownerRecord = ownerRecords.find((r) => r.uuid === uuid);
                            if (ownerRecord && record) {
                                this.env[modelName].write([ownerRecord.id], { [name]: record[0] });
                            }
                        }
                    }
                }
            }
        }

        return this.read_pos_data(orderIds, data, this.config_id);
    }

    read_pos_data(orderIds, data, config_id) {
        const posOrder = [];
        const posSession = [];
        const posPayment = [];
        const posOrderLine = [];
        const posPackOperationLot = [];
        const posCustomAttributeValue = [];
        const readOrder = this.read(orderIds, this._load_pos_data_fields(config_id), false);

        for (const order of readOrder) {
            posOrder.push(order);

            const lines = this.env["pos.order.line"].read(
                order.lines,
                this.env["pos.order.line"]._load_pos_data_fields(config_id),
                false
            );
            const payments = this.env["pos.payment"].read(
                order.payment_ids,
                this.env["pos.payment"]._load_pos_data_fields(config_id),
                false
            );
            const packLotLineIds = lines.flatMap((line) => line.pack_lot_ids);
            const packLotLines = this.env["pos.pack.operation.lot"].read(
                packLotLineIds,
                this.env["pos.pack.operation.lot"]._load_pos_data_fields(config_id),
                false
            );
            const customAttributeValueIds = lines.flatMap(
                (line) => line.custom_attribute_value_ids
            );
            const customAttributeValues = this.env["product.attribute.custom.value"].read(
                customAttributeValueIds,
                this.env["product.attribute.custom.value"]._load_pos_data_fields(config_id),
                false
            );

            posOrderLine.push(...lines);
            posPayment.push(...payments);
            posPackOperationLot.push(...packLotLines);
            posCustomAttributeValue.push(...customAttributeValues);
        }

        return {
            "pos.order": posOrder,
            "pos.session": posSession,
            "pos.payment": posPayment,
            "pos.order.line": posOrderLine,
            "pos.pack.operation.lot": posPackOperationLot,
            "product.attribute.custom.value": posCustomAttributeValue,
        };
    }
}
