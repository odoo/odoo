// @ts-check
/** @odoo-module native */

import { shallowEqual } from "@web/core/utils/collections/objects";

/** @import { RelationalModelConfig } from "./relational_model.js" */

/** @import { SearchParams } from "@web/model/types" */

/**
 * @typedef {object} ConfigTransitionDeps
 * @property {number} [maxGroupByDepth]
 * @property {any[]} [defaultOrderBy]
 * @property {boolean} hasRoot
 */

/**
 * @template T
 * @param {Record<string, any>} params
 * @param {string} key
 * @param {T} fallback
 * @returns {T}
 */
function pickParam(params, key, fallback) {
    return key in params ? params[key] : fallback;
}

/**
 * @param {RelationalModelConfig} currentConfig
 * @param {Partial<SearchParams>} params
 * @param {ConfigTransitionDeps} deps
 * @returns {RelationalModelConfig}
 */
export function computeNextConfig(currentConfig, params, deps) {
    const { maxGroupByDepth, defaultOrderBy, hasRoot } = deps;
    const currentGroupBy = currentConfig.groupBy;
    const config = { ...currentConfig };

    config.context = pickParam(params, "context", config.context);
    config.context = { ...config.context };

    if (currentConfig.isMonoRecord) {
        config.mode = pickParam(params, "mode", config.mode);
        config.resId = pickParam(params, "resId", config.resId);
        config.resIds = pickParam(params, "resIds", config.resIds);
        if (!config.resIds) {
            config.resIds = config.resId ? [config.resId] : [];
        }
        if (!config.resId && config.mode !== "edit") {
            config.mode = "edit";
        }
    } else {
        config.domain = pickParam(params, "domain", config.domain);

        config.groupBy = pickParam(params, "groupBy", config.groupBy);
        if (maxGroupByDepth) {
            config.groupBy = config.groupBy.slice(0, maxGroupByDepth);
        }
        config.groupBy = config.groupBy.map((g) => {
            if (
                g in config.fields &&
                ["date", "datetime"].includes(config.fields[g].type)
            ) {
                return `${g}:month`;
            }
            return g;
        });

        config.orderBy = pickParam(params, "orderBy", config.orderBy);
        if (!config.orderBy.length) {
            config.orderBy = currentConfig.orderBy || [];
        }
        if (defaultOrderBy && !config.orderBy.length) {
            config.orderBy = defaultOrderBy;
        }

        if (!shallowEqual(config.groupBy || [], currentGroupBy || [])) {
            delete config.groups;
        } else if (config.groups) {
            config.groups = cloneGroupTree(config.groups);
        }
        if (!config.groupBy.length) {
            config.orderBy = config.orderBy.filter((order) => order.name !== "__count");
        }
    }
    if (!config.isMonoRecord) {
        if (params.domain) {
            const resetOffset = (/** @type {Record<string, any>} */ cfg) => {
                cfg.offset = 0;
                for (const group of Object.values(cfg.groups || {})) {
                    resetOffset(group.list);
                }
            };
            if (hasRoot) {
                resetOffset(config);
            }
        }
        if (!!config.groupBy.length !== !!currentGroupBy?.length) {
            delete config.limit;
        }
    }

    return config;
}

/**
 * @param {Record<string, any>} groups
 * @returns {Record<string, any>}
 */
export function cloneGroupTree(groups) {
    return Object.fromEntries(
        Object.entries(groups).map(([value, groupConfig]) => {
            const cloned = {
                ...groupConfig,
                list: {
                    ...groupConfig.list,
                    groups: groupConfig.list?.groups
                        ? cloneGroupTree(groupConfig.list.groups)
                        : groupConfig.list?.groups,
                },
            };
            if (groupConfig.record) {
                cloned.record = { ...groupConfig.record };
            }
            return [value, cloned];
        }),
    );
}
