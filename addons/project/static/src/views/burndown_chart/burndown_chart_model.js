/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { GraphModel } from "@web/views/graph/graph_model";
import { sortBy } from "@web/core/utils/arrays";

export class BurndownChartModel extends GraphModel {
    /**
     * @override
     */
    setup(params) {
        super.setup(params);
        this.stageSeqAndNamePerId = {};
    }

    /**
     * Fetch the sequence of each stage in the project. This function alters this.stageSeqAndNamePerId
     * @protected
     * @param {Object} context
     */
    async _fetchStageInfo(context) {
        const searchDomain =
            !context.active_id || !context.default_project_id
                ? []
                : [["project_ids", "in", context.active_id]];
        const data = await this.orm.webSearchRead("project.task.type", searchDomain, {
            specification: {
                name: {},
                sequence: {},
            },
        });
        const stageSeqAndNamePerId = {};
        for (const { id, name, sequence } of data.records) {
            stageSeqAndNamePerId[id] = { name, sequence };
        }
        return stageSeqAndNamePerId;
    }

    /**
     * @param {SearchParams} searchParams
     */
    async load(searchParams) {
        const { context, groupBy } = searchParams;

        if (groupBy.includes("stage_id")) {
            if (context.stage_name_and_sequence_per_id && context.default_project_id) {
                this.stageSeqAndNamePerId = context.stage_name_and_sequence_per_id;
            } else {
                // if the stage_name_and_sequence_per_id wasn't given by the action (for example if the page is simply reloaded)
                this.stageSeqAndNamePerId = await this._fetchStageInfo(context);
            }
        } else {
            this.stageSeqAndNamePerId = {};
        }
        await super.load(searchParams);
    }

    /**
     * @override
     */
    _prepareData() {
        super._prepareData();
        const { groupBy } = this.searchParams;
        const { mode } = this.metaData;
        if (mode === "line" && groupBy.includes("stage_id")) {
            this.data.datasets = sortBy(this.data.datasets, (dataSet) => {
                const firstIdentifier = [...dataSet.identifiers][0];
                const group = Object.assign(...JSON.parse(firstIdentifier));
                const val = group.stage_id;
                if (Array.isArray(val)) {
                    return this.stageSeqAndNamePerId[val[0]]?.sequence || -1;
                }
                return -1;
            });
        }
    }

    /**
     * @protected
     * @override
     */
    async _loadDataPoints(metaData) {
        metaData.measures.__count.string = _t("# of Tasks");
        return super._loadDataPoints(metaData);
    }
}
