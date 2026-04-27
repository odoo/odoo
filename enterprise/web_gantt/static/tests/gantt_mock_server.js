import { makeKwArgs, onRpc } from "@web/../tests/web_test_helpers";

onRpc("get_gantt_data", function getGanttData({ kwargs, model }) {
    const lazy = !kwargs.limit && !kwargs.offset && kwargs.groupby.length === 1;
    const { groups, length } = this.env[model].web_read_group({
        ...kwargs,
        lazy,
        fields: ["__record_ids:array_agg(id)"],
    });

    const recordIds = [];
    for (const group of groups) {
        recordIds.push(...(group.__record_ids || []));
    }

    const { records } = this.env[model].web_search_read(
        [["id", "in", recordIds]],
        kwargs.read_specification,
        makeKwArgs({ context: kwargs.context })
    );

    const unavailabilities = {};
    for (const fieldName of kwargs.unavailability_fields || []) {
        unavailabilities[fieldName] = {};
    }

    const progress_bars = {};
    for (const fieldName of kwargs.progress_bar_fields || []) {
        progress_bars[fieldName] = {};
    }

    return {
        groups,
        length,
        records,
        unavailabilities,
        progress_bars,
    };
});
