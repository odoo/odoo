import { RelationalModel } from "@web/model/relational_model/relational_model";

const ROTTING_AGGREGATE = "is_rotting:sum";

/**
 * Counts the rotting records of each group within web_read_group (see
 * mail.tracking.duration.mixin), as only a part of them may be loaded.
 */
export function RottingModelMixin(Model) {
    class RottingDynamicRecordList extends Model.DynamicRecordList {
        setup(config, data) {
            super.setup(...arguments);
            this.hasRottingAggregate = "is_rotting" in (data.aggregates || {});
            this._unloadedRottingCount = this.hasRottingAggregate
                ? data.aggregates.is_rotting - this._getLoadedRottingCount()
                : 0;
        }

        get rottingCount() {
            return this._unloadedRottingCount + this._getLoadedRottingCount();
        }

        _getLoadedRottingCount() {
            return this.records.filter((record) => record.data.is_rotting).length;
        }

        _setData(data) {
            if (!this.hasRottingAggregate) {
                return super._setData(data);
            }
            const rottingCount = this.rottingCount;
            super._setData(data);
            this._unloadedRottingCount = rottingCount - this._getLoadedRottingCount();
        }
    }

    /**
     * Requests the count of rotting records of each group as an additional aggregate. As
     * is_rotting is not an aggregatable field, the base model neither requests it nor reads it
     * from the response, so it is added to the aggregates of the groups here.
     */
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
            if (!config.fields.is_rotting) {
                return result;
            }
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
