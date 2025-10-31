// @ts-check
import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { cartesian, sections } from "@web/core/utils/arrays";
import { addPropertyFieldDefs } from "@web/model/model";
import { helpers, EvaluationError } from "@odoo/o-spreadsheet";

const { deepEquals } = helpers;

export const NO_RECORD_AT_THIS_POSITION = "__NO_RECORD_AT_THIS_POSITION__";

/**
 * @typedef {import("@web/core/orm_service").ORM} ORM
 * @typedef {import("@spreadsheet/data_sources/server_data").ServerData} ServerData
 * @typedef {import("@spreadsheet/data_sources/odoo_data_provider").OdooDataProvider} OdooDataProvider
 * @typedef {import("@spreadsheet").OdooGetters} OdooGetters
 * @typedef {import("@spreadsheet/pivot/odoo_pivot").OdooPivotRuntimeDefinition} OdooPivotRuntimeDefinition
 * @typedef {import("@odoo/o-spreadsheet").PivotMeasure} PivotMeasure
 * @typedef {import("@odoo/o-spreadsheet").PivotDomain} PivotDomain
 * @typedef {import("@odoo/o-spreadsheet").PivotDimension} PivotDimension
 */

/**
 * # On custom groups:
 *
 * In spreadsheet, we have a feature allowing for the user to define custom groups in pivots, ie. they can select two
 * values of a groupBy and decide to group them together. This will create a new custom field that will contains the
 * custom groups.
 *
 * The server is unaware of these custom fields, so we have to do the aggregation client side. This section will detail
 * how it is achieved. Let's take this pivot as an example:
 *
 *  _______________________________________________________________________________________________________
 * |                                |                                                                       |
 * |                                |                     Pipeline Analysis by Stage                        |
 * |                                |_______________________________________________________________________|
 * |                                |                Start               |               End                |
 * |                                |____________________________________|__________________________________|________________
 * |                                |   New            |  Qualified      |  Proposition    |  Won           |  Total         |
 * |________________________________|__________________|_________________|_________________|________________|________________|
 * |                                |    Exp. Rev.     |    Exp. Rev.    |    Exp. Rev.    |   Exp. Rev.    |   Exp. Rev.    |
 * |________________________________|__________________|_________________|_________________|________________|________________|
 * | Total                          |  $104,000.00     |  $87,300.00     |  $105,100.00    |  $23,800.00    |  $320,200.00   |
 * |________________________________|__________________|_________________|_________________|________________|________________|
 *
 * Here we have two levels of groupBy:
 * - the first one is stage_id (New, Qualified, Proposition, Won)
 * - the second one is a custom field that groups the stages into two groups: Start (New, Qualified) and
 *      End (Proposition, Won). We'll call this custom field custom_stage.
 *
 *
 * ############### RPC
 *
 * The groupBys of the pivot are then ["stage_id", "custom_stage"]. But since the server is unaware of custom_stage, we'll
 * first need to change the RPC to something the server can give us results for.
 *
 * This is done in `_getGroupsSubdivision`. The rest of the pivot model is also unaware of the custom groups, so it will
 * give the RPC parameters as if the custom group was a standard group.
 *
 * In our pivot, the `groupingSets` of the RPC will be:
 *          `[[], ["custom_stage"], ["custom_stage", "stage_id"]]`
 *
 * Simply replacing the custom_stage with it's parent groupBy, will give us:
 *          `[[], ["stage_id"], ["stage_id", "stage_id"]]`
 *
 * The server doesn't support duplicate groupBys (and they are useless), so we need a bit of processing to remove the
 * duplicates and get the grouping sets that will be used in the RPC:
 *          `[[], ["stage_id"]]`
 *
 * The server result will look something like this:
 * [
 *   {
 *     rowGroupBy: [],
 *     colGroupBy: [],
 *     subGroups: [{ "expected_revenue:sum": 320200 }],
 *   },
 *   {
 *     rowGroupBy: [],
 *     colGroupBy: ["stage_id"],
 *     subGroups: [
 *       { stage_id: [1, "New"],         "expected_revenue:sum": 104000 },
 *       { stage_id: [2, "Qualified"],   "expected_revenue:sum": 87300 },
 *       { stage_id: [3, "Proposition"], "expected_revenue:sum": 105100 },
 *       { stage_id: [4, "Won"],         "expected_revenue:sum": 23800 },
 *     ],
 *   },
 * ]
 *
 * Note that this is not included for brevity sake, but the subGroups also contain the domains and _count for each group.
 *
 *
 * ############### Aggregating subGroups
 *
 * Now that we have the subgroups, we need to aggregate them to have the value of the custom groups. This'll be done in
 * `_addCustomGroupsToGroup`, for each groupBys of our original grouping sets. Let's focus on our original grouping
 *  set of `["custom_stage"]`.
 *
 * The first step is to add the value of the custom field to all the subgroups. We'll have something like this:
 *    subGroups: [
 *       { stage_id: [1, "New"],         custom_stage: "start", "expected_revenue:sum": 104000 },
 *       { stage_id: [2, "Qualified"],   custom_stage: "start", "expected_revenue:sum": 87300 },
 *       { stage_id: [3, "Proposition"], custom_stage: "end",   "expected_revenue:sum": 105100 },
 *       { stage_id: [4, "Won"],         custom_stage: "end",   "expected_revenue:sum": 23800 },
 *     ]
 *
 *  We can now use `Object.groupBy` to group the subGroups with the same groupBy values. We'll end up with something like this:
 *  Object.groupBy result: {
 *    '["Start"]': [
 *        { stage_id: [1, "New"], "expected_revenue:sum": 104000, Stage2: "Start" },
 *        { stage_id: [2, "Qualified"], "expected_revenue:sum": 87300, Stage2: "Start" },
 *    ],
 *    '["End"]': [
 *        { stage_id: [3, "Proposition"], "expected_revenue:sum": 105100, Stage2: "End" },
 *        { stage_id: [4, "Won"], "expected_revenue:sum": 23800, Stage2: "End" },
 *    ],
 * }
 *
 * It is now simple to aggregate this (`_aggregateSubGroups`) to get our final subgroups. In our example, we just need to sum the
 * "expected_revenue:sum" for each group. The domains of each subGroups will also be aggregated with `OR` operators.
 * final subgroups: [
 *    { stage_id: [1, "New"], "expected_revenue:sum": 191300, Stage2: "Start" },
 *    { stage_id: [3, "Proposition"], "expected_revenue:sum": 128900, Stage2: "End" },
 * ]
 *
 * Note: Client side aggregation works with every aggregator but `count_distinct` where it's impossible to aggregate client-side.
 * This is why custom groups are disabled when a measure with `count_distinct` is used.
 *
 * The last step is to sort the subGroups if needed (`_sortCustomFieldsInSubGroups`), and voilà ! We have done the client-side
 * grouping of the custom fields.
 */

export class PivotDataProvider {
    /**
     * @param {OdooDataProvider} odooDataProvider
     * @param {OdooPivotRuntimeDefinition} definition
     */
    constructor(odooDataProvider, definition) {
        this.orm = odooDataProvider.orm;
        this.serverData = odooDataProvider.serverData;
        this.definition = definition;
    }

    async load({ context, domain }) {
        this.colGroupBys = this.definition.columns.map((c) => c.nameWithGranularity);
        this.rowGroupBys = this.definition.rows.map((r) => r.nameWithGranularity);
        await addPropertyFieldDefs(
            this.orm,
            this.definition.model,
            context,
            this.definition.fields,
            new Set([...this.rowGroupBys, ...this.colGroupBys])
        );

        const leftDivisors = sections(this.rowGroupBys);
        const rightDivisors = sections(this.colGroupBys);
        const divisors = cartesian(leftDivisors, rightDivisors);

        const groupSubdivisions = await this._subdivideGroup(divisors, context, domain);
        return groupSubdivisions;
    }

    /**
     * This method is used to compute the aggregate spec of a measurement in the
     * data of the web model. It's needed since we support to define an
     * aggregator for a field.
     */
    _getAggregateSpec(measure) {
        if (measure.fieldName === "__count") {
            return "__count";
        }
        if (measure.aggregator) {
            return `${measure.fieldName}:${measure.aggregator}`;
        }
        if (measure.type === "many2one") {
            return `${measure.fieldName}:count_distinct`;
        }
        const field = this.definition.fields[measure.fieldName];
        if (!field.aggregator) {
            throw new Error(`Field ${measure.fieldName} doesn't have a default aggregator`);
        }
        return `${measure.fieldName}:${field.aggregator}`;
    }

    _getMeasureSpecs() {
        return this.definition.measures
            .filter((measure) => !measure.computedBy)
            .map(this._getAggregateSpec, this);
    }

    /**
     * @protected
     * @param {string[]} rowGroupBy
     * @param {string[]} colGroupBy
     * @returns {string[]}
     */
    _getGroupBySpecs(rowGroupBy, colGroupBy) {
        const set = rowGroupBy.concat(colGroupBy).reduce((acc, gb) => {
            acc.add(this._normalize(gb));
            return acc;
        }, new Set());
        return [...set];
    }

    /**
     * @protected
     * @param {string} gb
     * @returns {string}
     */
    _normalize(gb) {
        const [fieldName, interval] = gb.split(":");
        const field = this.definition.fields[fieldName];
        if (!field) {
            throw new EvaluationError(_t("Field %s does not exist", fieldName));
        }
        if (["date", "datetime"].includes(field.type)) {
            return `${fieldName}:${interval || "month"}`;
        } else {
            return fieldName;
        }
    }

    /**
     * Get all partitions of a given group using the provided list of divisors
     * and enrich the objects of this.data.rowGroupTree, colGroupTree,
     * measurements, counts.
     *
     * @protected
     * @param {Array[]} divisors
     */
    async _subdivideGroup(divisors, context, domain) {
        const subGroup = {
            rowValues: [],
            colValues: [],
        };
        const groupDomain = domain;
        const measureSpecs = this._getMeasureSpecs();
        if (!measureSpecs.includes("__count")) {
            measureSpecs.push("__count");
        }
        const groupingSets = [];
        const groupInfo = [];
        divisors.forEach((divisor) => {
            const groupBy = this._getGroupBySpecs(divisor[0], divisor[1]);
            const key = JSON.stringify(groupBy.toSorted());
            let index = groupingSets.findIndex((value) => JSON.stringify(value.toSorted()) === key);
            if (index === -1) {
                index = groupingSets.length;
                groupingSets.push(groupBy);
            }
            groupInfo.push({
                group: subGroup,
                rowGroupBy: divisor[0],
                colGroupBy: divisor[1],
                subGroupIndex: index,
            });
        });

        const params = {
            resModel: this.definition.model,
            groupDomain,
            measureSpecs,
            groupingSets,
            kwargs: { context: context },
        };
        const groupSubdivisions = await this._getGroupsSubdivision(params, groupInfo);
        return groupSubdivisions;
    }

    async _getGroupsSubdivision(params, groupInfo) {
        const customFields = this.definition.customFields || {};

        const { columns, rows } = this.definition;
        const allGroupBys = params.groupingSets.flat();
        const order = columns
            .concat(rows)
            .filter(
                (dimension) =>
                    dimension.order && allGroupBys.includes(dimension.nameWithGranularity)
            )
            .map((dimension) => `${dimension.nameWithGranularity} ${dimension.order}`)
            .join(",");
        params.kwargs.order = order;

        const hasCustomField = allGroupBys.some((gb) => customFields[gb] !== undefined);
        if (!hasCustomField) {
            return await this._doFormattedReadGroupingSets(params, groupInfo);
        } else if (params.measureSpecs.some((measure) => measure.endsWith(":count_distinct"))) {
            throw new Error(_t('Cannot use custom pivot groups with "Count Distinct" measure'));
        } else {
            return this._doCustomGroupSubdivision(params, groupInfo);
        }
    }

    /**
     * If the measures can be aggregated client side (not `count_distinct`), we can do a single RPC to get all the
     * subgroups, then do a Object.groupBy() client side to aggregate the subgroups.
     *
     * See comment at the start of the file for more details.
     */
    async _doCustomGroupSubdivision(params, groupInfo) {
        const customFields = this.definition.customFields || {};

        const mockGroupInfo = groupInfo.map((info) => ({
            ...info,
            rowGroupBy: info.rowGroupBy.map((gb) => customFields[gb]?.parentField || gb),
            colGroupBy: info.colGroupBy.map((gb) => customFields[gb]?.parentField || gb),
        }));

        // Grouping sets need to be unique, but with custom groups some might be duplicated. It happens when we do
        // something like groupBy=[grouped:user_id, user_id], we only want to fetch groupBy=[user_id]
        const groupInfoKeysSet = new Set();
        const uniqueGroupInfo = [];
        for (const info of mockGroupInfo) {
            const { rowGroupBy, colGroupBy } = info;
            const uniqueGroups = [...new Set([...rowGroupBy, ...colGroupBy].sort())].join(",");
            if (!groupInfoKeysSet.has(uniqueGroups)) {
                uniqueGroupInfo.push({
                    ...info,
                    rowGroupBy,
                    colGroupBy,
                    subGroupIndex: groupInfoKeysSet.size,
                });
                groupInfoKeysSet.add(uniqueGroups);
            }
        }
        const uniqueGroupingSets = [...groupInfoKeysSet].map((key) =>
            key.split(",").filter((gb) => gb !== "")
        );

        // Remove custom groups from order
        if (params.kwargs.order) {
            const fieldNameRegex = /(.*) (asc|desc)/;
            params.kwargs.order = params.kwargs.order
                .split(",")
                .filter((part) => {
                    const groupBy = part.match(fieldNameRegex)?.[1];
                    return customFields[groupBy] === undefined;
                })
                .join(",");
        }

        const result = await this._doFormattedReadGroupingSets(
            { ...params, groupingSets: uniqueGroupingSets },
            uniqueGroupInfo
        );

        const resultWithCustomGroups = [];
        for (let i = 0; i < groupInfo.length; i++) {
            const info = groupInfo[i];
            const mockInfo = mockGroupInfo[i];
            const mockGroupBys = [
                ...new Set([...mockInfo.rowGroupBy, ...mockInfo.colGroupBy].sort()),
            ];
            const resultIndex = uniqueGroupingSets.findIndex((groups) =>
                deepEquals(groups, mockGroupBys)
            );
            const subGroups = result[resultIndex].subGroups;

            const groupBys = [...info.rowGroupBy, ...info.colGroupBy];
            const hasCustomField = groupBys.some((gb) => customFields[gb] !== undefined);
            if (hasCustomField) {
                resultWithCustomGroups.push(this._addCustomGroupsToGroup(params, info, subGroups));
            } else {
                resultWithCustomGroups.push({ ...info, subGroups });
            }
        }
        return resultWithCustomGroups;
    }

    async _doFormattedReadGroupingSets(params, groupInfo) {
        const { resModel, groupDomain, groupingSets, measureSpecs, kwargs } = params;
        const result = await this.orm.formattedReadGroupingSets(
            resModel,
            groupDomain,
            groupingSets,
            measureSpecs,
            kwargs
        );
        return groupInfo.map((info) => ({ ...info, subGroups: result[info.subGroupIndex] }));
    }

    _addCustomGroupsToGroup(params, groupInfo, subGroups) {
        const customFields = this.definition.customFields || {};
        const { rowGroupBy, colGroupBy } = groupInfo;
        const groupBys = [...rowGroupBy, ...colGroupBy];

        for (const groupBy of groupBys) {
            const customField = customFields[groupBy];
            if (!customField) {
                continue;
            }

            for (const subGroup of subGroups) {
                const parentFieldName = customField.parentField;
                const parentValue = Array.isArray(subGroup[parentFieldName])
                    ? subGroup[parentFieldName][0]
                    : subGroup[parentFieldName];
                const group =
                    customField.groups.find((g) => g.values.includes(parentValue)) ||
                    customField.groups.find((g) => g.isOtherGroup);

                subGroup[groupBy] = group ? group.name : subGroup[parentFieldName];
            }
        }

        // Note: we need to preserve the order of the subGroups from the server. Object.groupBy() has no guarantee
        // on the order of keys, but its implementation in major browsers does seem to preserve the order. We'll use
        // Object.groupBy() until we find practical issues with it.
        const getKey = (subGroup) => JSON.stringify(groupBys.map((groupBy) => subGroup[groupBy]));
        const groupedSubgroups = Object.groupBy(subGroups, getKey);

        const aggregatedSubgroups = Object.values(groupedSubgroups).map((subGroups) =>
            this._aggregateSubGroups(subGroups, params.measureSpecs)
        );
        const sortedSubGroups = this._sortCustomFieldsInSubGroups(groupBys, aggregatedSubgroups);

        return { ...groupInfo, subGroups: sortedSubGroups };
    }

    _aggregateSubGroups(subGroups, measures) {
        if (subGroups.length === 1) {
            return subGroups[0];
        }
        const subGroup = { ...subGroups[0] };
        for (const measure of measures) {
            const aggregator = measure.split(":")[1];
            switch (aggregator) {
                case "sum":
                case "count":
                    subGroup[measure] = subGroups.reduce((sum, sg) => sum + sg[measure], 0);
                    break;
                case "min":
                    subGroup[measure] = Math.min(...subGroups.map((sg) => sg[measure]));
                    break;
                case "max":
                    subGroup[measure] = Math.max(...subGroups.map((sg) => sg[measure]));
                    break;
                case "avg": {
                    const totalCount = subGroups.reduce((sum, sg) => sum + (sg.__count || 0), 0);
                    if (totalCount === 0) {
                        subGroup[measure] = 0;
                    } else {
                        subGroup[measure] =
                            subGroups.reduce((sum, sg) => sum + sg[measure] * sg.__count, 0) /
                            totalCount;
                    }
                    break;
                }
            }
        }
        subGroup.__count = subGroups.reduce((sum, sg) => sum + (sg.__count || 0), 0);

        const domains = subGroups.map((sg) => sg.__domain || []);
        subGroup.__domain = Domain.combine(domains, "OR").toList();
        const extraDomains = subGroups.map((sg) => sg.__extraDomain || []);
        subGroup.__extraDomain = Domain.combine(extraDomains, "OR").toList();

        return subGroup;
    }

    _sortCustomFieldsInSubGroups(groupBys, subGroups) {
        const isInOthersGroup = (subGroup, groupBy, customField) => {
            const value = Array.isArray(subGroup[groupBy])
                ? subGroup[groupBy][0]
                : subGroup[groupBy];
            const otherGroup = customField.groups.find((g) => g.isOtherGroup);
            return otherGroup && value === otherGroup.name;
        };

        const sortFn = (subGroupA, subGroupB, order, groupBy, customField) => {
            if (isInOthersGroup(subGroupB, groupBy, customField)) {
                return -1;
            }
            if (isInOthersGroup(subGroupA, groupBy, customField)) {
                return 1;
            }
            const aValue = subGroupA[groupBy];
            const bValue = subGroupB[groupBy];
            if (aValue === false) {
                return order === "asc" ? 1 : -1;
            } else if (bValue === false) {
                return order === "asc" ? -1 : 1;
            }

            const aLabel = (Array.isArray(aValue) ? aValue[1] : String(aValue)).toLowerCase();
            const bLabel = (Array.isArray(bValue) ? bValue[1] : String(bValue)).toLowerCase();
            return order === "asc" ? aLabel.localeCompare(bLabel) : bLabel.localeCompare(aLabel);
        };

        const sortSubGroups = (groupBys, subGroups) => {
            const groupBy = groupBys[0];
            const childrenMap = new Map();

            for (const item of subGroups) {
                const value = item[groupBy];
                const key = Array.isArray(value) ? value[0] : value;
                if (!childrenMap.has(key)) {
                    childrenMap.set(key, []);
                }
                childrenMap.get(key).push(item);
            }

            // Sort group keys
            const customField = this.definition.customFields?.[groupBy];
            const keys = Array.from(childrenMap.keys());
            const order = this.definition.getDimension(groupBy)?.order;

            if (customField && order) {
                keys.sort((a, b) => {
                    const subGroupB = childrenMap.get(b)[0];
                    const subGroupA = childrenMap.get(a)[0];
                    return sortFn(subGroupA, subGroupB, order, groupBy, customField);
                });
            }

            return keys.flatMap((key) =>
                groupBys.length > 1
                    ? sortSubGroups(groupBys.slice(1), childrenMap.get(key))
                    : childrenMap.get(key)
            );
        };

        return sortSubGroups(groupBys, subGroups);
    }

    /**
     * @param {string} resModel
     * @param {number} resId
     * @returns {string}
     */
    loadRelationalDisplayName(resModel, resId) {
        return this.serverData.batch.get("spreadsheet.mixin", "get_display_names_for_spreadsheet", {
            model: resModel,
            id: resId,
        });
    }
}
