import { models, Command } from "@web/../tests/web_test_helpers";

const { DateTime } = luxon;

export class PosOrder extends models.ServerModel {
    _name = "pos.order";

    read_pos_orders(domain) {
        const results = this.search(domain, this._load_pos_data_fields(), false);
        return this.read_pos_data(results);
    }

    _load_pos_data_fields() {
        return [];
    }

    cancel_order_from_pos(self) {
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

    get_receipt_template_for_pos_frontend() {
        return [];
    }

    sync_from_ui(data) {
        const orderIds = [];
        for (const record of data) {
            record.write_date = DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss");
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

    record_uuid_mapping(uuidMapping) {
        for (const [model, data] of Object.entries(uuidMapping)) {
            for (const [uuid, fields] of Object.entries(data)) {
                const record = this.env[model].search_read([["uuid", "=", uuid]], []);
                if (record.length === 0) {
                    continue;
                }

                for (const [fieldName, vals] of Object.entries(fields)) {
                    const relation = this.env[model]._fields[fieldName].relation;
                    if (!relation) {
                        continue;
                    }

                    const rels = this.env[relation].search_read([["uuid", "in", vals]], ["id"]);
                    const ids = rels.map((r) => r.id);
                    if (ids.length === 0) {
                        continue;
                    }

                    const value = Array.isArray(vals) ? [...ids, ...record[fieldName]] : ids[0];
                    console.log("David ", value);
                    this.env[model].write([record[0].id], { [fieldName]: value });
                }
            }
        }
    }

    read_pos_data(orderIds, data, config_id) {
        const posOrder = [];
        const posSession = [];
        const posPayment = [];
        const posOrderLine = [];
        const posCustomAttributeValue = [];
        const posPrepOrder = [];
        const posPrepLine = [];
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
            const customAttributeValueIds = lines.flatMap(
                (line) => line.custom_attribute_value_ids
            );
            const customAttributeValues = this.env["product.attribute.custom.value"].read(
                customAttributeValueIds,
                this.env["product.attribute.custom.value"]._load_pos_data_fields(config_id),
                false
            );

            let prepOrders = [];
            let prepLines = [];

            if (order.prep_order_ids.length > 0) {
                prepOrders = this.env["pos.prep.order"].read(
                    order.prep_order_ids,
                    this.env["pos.prep.order"]._load_pos_data_fields(config_id),
                    false
                );
            }

            if (prepOrders.length > 0) {
                prepLines = this.env["pos.prep.line"].read(
                    prepOrders.flatMap((po) => po.prep_line_ids),
                    this.env["pos.prep.line"]._load_pos_data_fields(config_id),
                    false
                );
            }

            posPrepOrder.push(...prepOrders);
            posPrepLine.push(...prepLines);
            posOrderLine.push(...lines);
            posPayment.push(...payments);
            posCustomAttributeValue.push(...customAttributeValues);
        }

        return {
            "pos.order": posOrder,
            "pos.session": posSession,
            "pos.payment": posPayment,
            "pos.order.line": posOrderLine,
            "product.attribute.custom.value": posCustomAttributeValue,
            "pos.prep.order": posPrepOrder,
            "pos.prep.line": posPrepLine,
        };
    }

    search_order_ids(config_id, domain, limit, offset) {
        return {
            ordersInfo: [],
            totalCount: 0,
        };
    }
}
