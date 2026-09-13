// @ts-check
/** @odoo-module native */

import { Domain } from "@web/core/domain";

import { makeActiveField } from "./field_metadata.js";
import { extractInfoFromGroupData } from "./field_values.js";
import { getGroupKey } from "./group_key.js";

/** @import { RelationalModelConfig } from "./relational_model.js" */

/**
 * @typedef {object} PostprocessReadGroupDeps
 * @property {(config: RelationalModelConfig, propertyFullName: string) => Promise<void>} getPropertyDefinition
 * @property {Record<string, { activeFields: Record<string, any>; fields: Record<string, any> }>} groupByInfo
 * @property {number} initialLimit
 * @property {number} initialGroupsLimit
 * @property {number} defaultGroupLimit
 * @typedef {object} ExtractContext
 * @property {RelationalModelConfig} rootConfig
 * @property {Record<string, any>} commonConfig
 * @property {PostprocessReadGroupDeps} deps
 */

/**
 * @param {ExtractContext} ctx
 * @param {string} groupByFieldName
 * @returns {Promise<void>}
 */
async function loadPropertyGroupBy(ctx, groupByFieldName) {
    if (!groupByFieldName.includes(".")) {
        return;
    }
    const { rootConfig, deps } = ctx;
    if (!rootConfig.fields[groupByFieldName]) {
        await deps.getPropertyDefinition(rootConfig, groupByFieldName);
    }
    const propertiesFieldName = groupByFieldName.split(".")[0];
    if (!rootConfig.activeFields[propertiesFieldName]) {
        rootConfig.activeFields[propertiesFieldName] = /** @type {any} */ (
            makeActiveField()
        );
    }
}

/**
 * @param {ExtractContext} ctx
 * @param {Record<string, any>} currentConfig
 * @param {Record<string, any>} group
 * @param {{ groupByFieldName: string, nextLevelGroupBy: string[] }} level
 * @returns {Record<string, any>}
 */
function upsertGroupConfig(ctx, currentConfig, group, level) {
    const { commonConfig, deps } = ctx;
    const { groupByFieldName, nextLevelGroupBy } = level;
    const key = getGroupKey(group.value);
    if (!Object.hasOwn(currentConfig.groups, key)) {
        const groupConfig = {
            ...commonConfig,
            groupByFieldName,
            extraDomain: false,
            value: group.value,
            list: {
                ...commonConfig,
                groupBy: nextLevelGroupBy,
                groups: {},
                limit: !nextLevelGroupBy.length
                    ? deps.initialLimit
                    : deps.initialGroupsLimit || deps.defaultGroupLimit,
            },
        };
        currentConfig.groups[key] = groupConfig;
    }

    const groupConfig = currentConfig.groups[key];
    groupConfig.list.orderBy = currentConfig.orderBy;
    groupConfig.initialDomain = group.domain;
    groupConfig.list.domain = groupConfig.extraDomain
        ? Domain.and([group.domain, groupConfig.extraDomain]).toList()
        : group.domain;
    const context = {
        ...currentConfig.context,
        [`default_${groupByFieldName}`]: group.serverValue,
    };
    groupConfig.list.context = context;
    groupConfig.context = context;
    return groupConfig;
}

/**
 * @param {ExtractContext} ctx
 * @param {Record<string, any>} group
 * @param {Record<string, any>} groupData
 * @param {Record<string, any>} groupConfig
 * @param {string[]} nextLevelGroupBy
 * @returns {Promise<void>}
 */
async function attachGroupContents(
    ctx,
    group,
    groupData,
    groupConfig,
    nextLevelGroupBy,
) {
    if (nextLevelGroupBy.length) {
        groupConfig.isFolded = !("__groups" in groupData);
        if (groupConfig.isFolded) {
            group.groups = [];
            return;
        }
        const { groups: nested, length: nestedLength } = groupData.__groups;
        group.groups = await extractGroups(ctx, groupConfig.list, nested);
        group.length = nestedLength;
        return;
    }
    groupConfig.isFolded = !("__records" in groupData);
    if (groupConfig.isFolded) {
        group.records = [];
        return;
    }
    group.records = groupData.__records;
    group.length = groupData.__count;
}

/**
 * @param {ExtractContext} ctx
 * @param {Record<string, any>} currentConfig
 * @param {Record<string, any>[]} groupsData
 * @returns {Promise<Record<string, any>[]>}
 */
async function extractGroups(ctx, currentConfig, groupsData) {
    const groupByFieldName = currentConfig.groupBy[0].split(":")[0];
    await loadPropertyGroupBy(ctx, groupByFieldName);

    const nextLevelGroupBy = currentConfig.groupBy.slice(1);
    const level = { groupByFieldName, nextLevelGroupBy };

    let groupRecordConfig;
    if (ctx.deps.groupByInfo[groupByFieldName]) {
        groupRecordConfig = {
            ...ctx.deps.groupByInfo[groupByFieldName],
            resModel: currentConfig.fields[groupByFieldName].relation,
            context: {},
        };
    }

    const out = [];
    for (const groupData of groupsData) {
        const group = /** @type {Record<string, any>} */ (
            extractInfoFromGroupData(
                groupData,
                currentConfig.groupBy,
                currentConfig.fields,
                currentConfig.domain,
                currentConfig.fieldsToAggregate,
            )
        );
        const groupConfig = upsertGroupConfig(ctx, currentConfig, group, level);
        await attachGroupContents(ctx, group, groupData, groupConfig, nextLevelGroupBy);
        if (Object.hasOwn(groupData, "__offset")) {
            groupConfig.list.offset = groupData.__offset;
        }
        if (groupRecordConfig) {
            groupConfig.record = {
                ...groupRecordConfig,
                resId: group.value ?? false,
            };
        }
        out.push(group);
    }
    return out;
}

/**
 * @param {RelationalModelConfig} config
 * @returns {string}
 */
function groupsIdentity(config) {
    return JSON.stringify([
        config.domain,
        config.groupBy,
        config.offset,
        config.limit,
        config.orderBy,
    ]);
}

/**
 * @param {RelationalModelConfig} config
 * @param {Record<string, any>[]} groups
 * @param {string} params
 * @returns {void}
 */
function reinsertEmptiedGroups(config, groups, params) {
    if (!config.currentGroups || config.currentGroups.params !== params) {
        return;
    }
    const currentGroups = /** @type {any[]} */ (config.currentGroups.groups);
    const mergedKeys = groups.map((g) => getGroupKey(g.value));
    const survivingKeys = new Set(mergedKeys);
    let cursor = 0;
    for (const group of currentGroups) {
        const key = getGroupKey(group.value);
        if (survivingKeys.has(key)) {
            cursor = Math.max(cursor, mergedKeys.indexOf(key) + 1);
            continue;
        }
        if (!Object.hasOwn(config.groups, key)) {
            continue;
        }
        const aggregates = { ...group.aggregates };
        for (const aggKey of Object.keys(aggregates)) {
            aggregates[aggKey] = Array.isArray(aggregates[aggKey]) ? [] : 0;
        }
        groups.splice(cursor, 0, {
            ...group,
            count: 0,
            length: 0,
            records: [],
            groups: [],
            aggregates,
        });
        mergedKeys.splice(cursor, 0, key);
        cursor++;
    }
}

/**
 * @param {RelationalModelConfig} config
 * @param {{ groups: any[]; length: number }} response
 * @param {PostprocessReadGroupDeps} deps
 * @returns {Promise<{ groups: any[]; length: number }>}
 */
export async function postprocessReadGroup(config, response, deps) {
    const { length } = response;
    /** @type {ExtractContext} */
    const ctx = {
        rootConfig: config,
        commonConfig: {
            resModel: config.resModel,
            fields: config.fields,
            activeFields: config.activeFields,
            fieldsToAggregate: config.fieldsToAggregate,
            offset: 0,
        },
        deps,
    };

    const groups = await extractGroups(ctx, config, response.groups);
    const params = groupsIdentity(config);
    reinsertEmptiedGroups(config, groups, params);
    config.currentGroups = { params, groups };

    return { groups, length };
}
