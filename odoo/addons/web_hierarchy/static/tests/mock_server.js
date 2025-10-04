/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.method === "hierarchy_read") {
            return this.mockHierarchyRead(args.model, args.args, args.kwargs);
        }
        return super._performRPC(route, args);
    },

    mockHierarchyRead(modelName, args, kwargs) {
        const [domain, fields, parentFieldName, childFieldName] = args;
        if (!(parentFieldName in fields)) {
            fields.push(parentFieldName);
        }
        let records = this.mockSearchRead(modelName, [domain, fields], kwargs);
        let focusedRecordId = false;
        let fetchChildIdsForAllRecords = false;
        if (records.length === 1) {
            const record = records[0];
            let domain = [[parentFieldName, "=", record.id], ["id", "!=", record.id]];
            if (record[parentFieldName]) {
                focusedRecordId = record.id;
                const parentResId = record[parentFieldName][0];
                domain = [
                    ["id", "!=", record.id],
                    "|",
                        ["id", "=", parentResId],
                        [parentFieldName, "in", [parentResId, record.id]],
                ];
            }
            records.push(...this.mockSearchRead(modelName, [domain, fields], kwargs));
        } else if (!records.length) {
            records = this.mockSearchRead(
                modelName,
                [
                    [[parentFieldName, "=", false]],
                    fields,
                ],
                kwargs,
            );
        } else {
            fetchChildIdsForAllRecords = true
        }
        const childrenIdsPerRecordId = {};
        if (!childFieldName) {
            const parentResIds = [];
            for (const rec of records) {
                if (rec[parentFieldName]) {
                    parentResIds.push(rec[parentFieldName][0]);
                }
            }
            const recordIds = records.map((rec) => rec.id);
            const data = this.mockReadGroup(modelName, {
                domain: [[parentFieldName, "in", fetchChildIdsForAllRecords ? recordIds : recordIds.filter((id) => !parentResIds.includes(id))]],
                groupby: [parentFieldName],
                fields: ["id:array_agg"],
            });
            for (const d of data) {
                childrenIdsPerRecordId[d[parentFieldName][0]] = d.id;
            }
        }
        if (focusedRecordId || Object.keys(childrenIdsPerRecordId).length) {
            for (const record of records) {
                if (record.id in childrenIdsPerRecordId) {
                    record.__child_ids__ = childrenIdsPerRecordId[record.id];
                }
                if (record.id === focusedRecordId) {
                    record.__focus__ = true;
                }
            }
        }
        return records;
    },
})
