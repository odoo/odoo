import { registry } from "@web/core/registry";

function _mockGetGanttData(_, { model, kwargs }) {
    const lazy = !kwargs.limit && !kwargs.offset && kwargs.groupby.length === 1;
    const { groups, length } = this.mockWebReadGroup(model, {
        ...kwargs,
        lazy,
        fields: ["__record_ids:array_agg(id)"],
    });

    const recordIds = [];
    for (const group of groups) {
        recordIds.push(...(group.__record_ids || []));
    }

    const { records } = this.mockWebSearchReadUnity(model, [], {
        domain: [["id", "in", recordIds]],
        context: kwargs.context,
        specification: kwargs.read_specification,
    });

    const unavailabilities = {};
    for (const fieldName of kwargs.unavailability_fields || []) {
        unavailabilities[fieldName] = {};
    }

    const progress_bars = {};
    for (const fieldName of kwargs.progress_bar_fields || []) {
        progress_bars[fieldName] = {};
    }

    return { groups, length, records, unavailabilities, progress_bars };
}

registry.category("mock_server").add("get_gantt_data", _mockGetGanttData);
