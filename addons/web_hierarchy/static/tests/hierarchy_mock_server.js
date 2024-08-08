import { makeKwArgs } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

function _mockHierarchyRead({ model, args, kwargs }) {
    kwargs = makeKwArgs(kwargs);
    const [domain, fields, parentFieldName, childFieldName, order] = args;
    kwargs.order = order;
    if (!(parentFieldName in fields)) {
        fields.push(parentFieldName);
    }
    const records = this.env[model].search_read(domain, kwargs);
    let focusedRecordId = false;
    let fetchChildIdsForAllRecords = false;
    if (!records.length) {
        return [];
    } else if (records.length === 1) {
        const record = records[0];
        let domain = [
            [parentFieldName, "=", record.id],
            ["id", "!=", record.id],
        ];
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
        records.push(...this.env[model].search_read(domain, kwargs));
    } else {
        fetchChildIdsForAllRecords = true;
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
        const data = this.env[model].web_read_group({
            ...kwargs,
            domain: [
                [
                    parentFieldName,
                    "in",
                    fetchChildIdsForAllRecords
                        ? recordIds
                        : recordIds.filter((id) => !parentResIds.includes(id)),
                ],
            ],
            groupby: [parentFieldName],
            fields: ["id:array_agg"],
        });
        for (const group of data.groups) {
            childrenIdsPerRecordId[group[parentFieldName][0]] = group.id;
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
}

registry.category("mock_rpc").add("hierarchy_read", _mockHierarchyRead);
