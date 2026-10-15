import { RelationalModel } from "@web/model/relational_model/relational_model";

const ROTTING_AGGREGATE = "is_rotting:sum";

/**
 * Counts the rotting records of each group within web_read_group (see
 * mail.tracking.duration.mixin), as only a part of them may be loaded.
 */
export function RottingModelMixin(Model) {
    class RottingDynamicRecordList extends Model.DynamicRecordList {
        setup(config, data) {
            this._unloadedRottingCount = data.aggregates?.is_rotting;
            super.setup(...arguments);
        }

        get rottingCount() {
            if (this._unloadedRottingCount === undefined) {
                return undefined;
            }
            return this._unloadedRottingCount + this._getLoadedRottingCount();
        }

        _getLoadedRottingCount() {
            return this.records.filter((record) => record.data.is_rotting).length;
        }

        _setData(data) {
            const rottingCount = this.records ? this.rottingCount : this._unloadedRottingCount;
            super._setData(data);
            if (rottingCount !== undefined) {
                this._unloadedRottingCount = rottingCount - this._getLoadedRottingCount();
            }
        }
    }

    class RottingModel extends Model {
        static DynamicRecordList = RottingDynamicRecordList;

        _getAggregateSpecifications(config) {
            const aggregates = super._getAggregateSpecifications(config);
            if (config.fields.is_rotting) {
                aggregates.push(ROTTING_AGGREGATE);
            }
            return aggregates;
        }

        async _postprocessReadGroup(config, response) {
            const result = await super._postprocessReadGroup(...arguments);
            const groupBy = config.groupBy[0];
            const rottingCounts = new Map(
                response.groups.map((group) => [
                    JSON.stringify(group[groupBy]),
                    group[ROTTING_AGGREGATE],
                ])
            );
            for (const group of result.groups) {
                group.aggregates.is_rotting = rottingCounts.get(JSON.stringify(group.rawValue)) || 0;
            }
            return result;
        }
    }

    return RottingModel;
}

export class RottingKanbanModel extends RottingModelMixin(RelationalModel) {}
