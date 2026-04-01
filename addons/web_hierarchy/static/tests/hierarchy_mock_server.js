import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("hierarchy_read", function hierarchyRead({ model, args, kwargs }) {
    const [domain, specification, parentFieldName, childFieldName, order] = args;
    kwargs.order = order;
    if (!(parentFieldName in specification)) {
        specification[parentFieldName] = { fields: { display_name: {} } };
    }
    const result = this.env[model].web_search_read(domain, specification, kwargs);
    let focusedRecordId = false;
    let fetchChildIdsForAllRecords = false;
    if (!result.length) {
        return [];
    }
    const records = result.records;
    if (result.length === 1) {
        const record = records[0];
        let domain = [
            [parentFieldName, "=", record.id],
            ["id", "!=", record.id],
        ];
        if (record[parentFieldName]) {
            focusedRecordId = record.id;
            const parentResId = record[parentFieldName].id;
            domain = [
                ["id", "!=", record.id],
                "|",
                ["id", "=", parentResId],
                [parentFieldName, "in", [parentResId, record.id]],
            ];
        }
        records.push(
            ...(this.env[model].web_search_read(domain, specification, kwargs)?.records || [])
        );
    } else {
        fetchChildIdsForAllRecords = true;
    }
    const childrenIdsPerRecordId = {};
    if (!childFieldName) {
        const parentResIds = [];
        for (const rec of records) {
            if (rec[parentFieldName]) {
                parentResIds.push(rec[parentFieldName].id);
            }
        }
        const recordIds = records.map((rec) => rec.id);
        const groups = this.env[model].formatted_read_group({
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
            aggregates: ["id:array_agg"],
        });
        for (const group of groups) {
            childrenIdsPerRecordId[group[parentFieldName][0]] = group["id:array_agg"];
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
});
