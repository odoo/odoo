import { registry } from "@web/core/registry";

function _mockGetGanttData(params) {
    const lazy = !params.limit && !params.offset && params.groupby.length === 1;
    let { groups, length } = this._mockWebReadGroup({
        ...params,
        lazy,
        fields: ["__record_ids:array_agg(id)"],
    });
    if (params.limit) {
        // we don't care about pager feature in sample mode
        // but we want to present something coherent
        groups = groups.slice(0, params.limit);
        length = groups.length;
    }
    groups.forEach((g) => (g.__record_ids = g.id)); // the sample server does not use the key __record_ids

    const recordIds = [];
    for (const group of groups) {
        recordIds.push(...(group.__record_ids || []));
    }

    const { records } = this._mockWebSearchReadUnity({
        model: params.model,
        domain: [["id", "in", recordIds]],
        context: params.context,
        specification: params.read_specification,
    });

    const unavailabilities = {};
    for (const fieldName of params.unavailability_fields || []) {
        unavailabilities[fieldName] = {};
    }

    const progress_bars = {};
    for (const fieldName of params.progress_bar_fields || []) {
        progress_bars[fieldName] = {};
    }

    return { groups, length, records, unavailabilities, progress_bars };
}

registry.category("sample_server").add("get_gantt_data", _mockGetGanttData);
