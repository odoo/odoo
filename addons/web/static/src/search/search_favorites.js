// @ts-check

/** @module search/search_favorites - Favorites/ir.filters utilities for SearchModel */

/** @import { OrderTerm } from "@web/core/utils/order_by" */

import { makeContext } from "@web/core/context";
import { evaluateExpr } from "@web/core/py_js/py";
import { user } from "@web/services/user";

import { FAVORITE_PRIVATE_GROUP, FAVORITE_SHARED_GROUP } from "./search_state";

/**
 * Convert an ir.filter record to a favorite search item.
 *
 * @param {Object} irFilter
 * @returns {Object} favorite search item (pre-group format)
 */
export function irFilterToFavorite(irFilter) {
    const userIds = irFilter.user_ids;
    const groupNumber =
        userIds.length === 1 ? FAVORITE_PRIVATE_GROUP : FAVORITE_SHARED_GROUP;
    const context = evaluateExpr(irFilter.context, user.context);
    let groupBys = [];
    if (context.group_by) {
        groupBys = Array.isArray(context.group_by)
            ? context.group_by
            : [context.group_by];
        delete context.group_by;
    }
    let sort;
    try {
        sort = JSON.parse(irFilter.sort);
    } catch (err) {
        if (err instanceof SyntaxError) {
            sort = [];
        } else {
            throw err;
        }
    }
    const orderBy = sort.map((order) => {
        let fieldName;
        let asc;
        const sqlNotation = order.split(" ");
        if (sqlNotation.length > 1) {
            fieldName = sqlNotation[0];
            asc = sqlNotation[1] === "asc";
        } else {
            fieldName = order[0] === "-" ? order.slice(1) : order;
            asc = order[0] !== "-";
        }
        return { asc, name: fieldName };
    });
    const favorite = {
        context,
        description: irFilter.name,
        domain: irFilter.domain,
        groupBys,
        groupNumber,
        orderBy,
        removable: true,
        serverSideId: irFilter.id,
        type: "favorite",
        userIds,
    };
    if (irFilter.is_default) {
        favorite.isDefault = irFilter.is_default;
    }
    return favorite;
}

/**
 * Reconciliate existing search items of type "favorite" with the current ir.filters.
 * Updates changed favorites, removes deleted ones, and creates new ones.
 *
 * @param {Object} searchItems - mutable searchItems map
 * @param {Object[]} query - mutable query array
 * @param {Object[]} irFilters
 * @param {Function} irFilterToFavoriteFn - conversion function (irFilter) => favorite
 * @param {Function} createGroupOfFavoritesFn - (irFilters) => void
 */
export function reconciliateFavorites(
    searchItems,
    query,
    irFilters,
    irFilterToFavoriteFn,
    createGroupOfFavoritesFn,
) {
    const filters = irFilters || [];
    const mapping = Object.fromEntries(filters.map((i) => [i.id, i]));
    for (const item of Object.values(searchItems)) {
        if (item.type !== "favorite") {
            continue;
        }
        const irFilter = mapping[item.serverSideId];
        if (irFilter) {
            Object.assign(item, irFilterToFavoriteFn(irFilter));
            delete mapping[item.serverSideId];
        } else {
            const queryIndex = query.findIndex((q) => q.searchItemId === item.id);
            if (queryIndex !== -1) {
                query.splice(queryIndex, 1);
            }
            delete searchItems[item.id];
        }
    }
    createGroupOfFavoritesFn(Object.values(mapping));
}

/**
 * Build the ir.filter description for saving a favorite.
 *
 * @param {Object} params
 * @param {string} params.description
 * @param {boolean} params.isDefault
 * @param {boolean} params.isShared
 * @param {number|false} [params.embeddedActionId]
 * @param {Object} params.localContext - context from env.__getContext__
 * @param {OrderTerm[]} [params.localOrderBy] - orderBy from env.__getOrderBy__
 * @param {Function} params.getContext - () => searchContext
 * @param {Function} params.getDomain - () => Domain (raw, no global)
 * @param {Function} params.getGroupBy - () => string[]
 * @param {Function} params.getOrderBy - () => OrderTerm[]
 * @param {Object} params.globalContext
 * @param {number} params.actionId
 * @param {string} params.resModel
 * @returns {{ preFavorite: Object, irFilter: Object }}
 */
export function buildIrFilterDescription({
    description,
    isDefault,
    isShared,
    embeddedActionId,
    localContext,
    localOrderBy,
    getContext,
    getDomain,
    getGroupBy,
    getOrderBy,
    globalContext,
    actionId,
    resModel,
}) {
    const context = makeContext([getContext(), localContext]);
    const userContext = user.context;
    for (const key in context) {
        if (key in userContext || /^search(panel)?_default_/.test(key)) {
            delete context[key];
        }
    }
    const domain = getDomain().toString();
    const groupBys = getGroupBy();
    const orderBy = localOrderBy || getOrderBy();
    const userIds = isShared ? [] : [user.userId];

    const preFavorite = {
        description,
        isDefault,
        domain,
        context,
        groupBys,
        orderBy,
        userIds,
    };
    const irFilter = {
        name: description,
        action_id: actionId,
        model_id: resModel,
        domain,
        embedded_action_id: embeddedActionId,
        embedded_parent_res_id: globalContext.active_id || false,
        is_default: isDefault,
        sort: JSON.stringify(
            orderBy.map((o) => `${o.name}${o.asc === false ? " desc" : ""}`),
        ),
        user_ids: userIds,
        context: { group_by: groupBys, ...context },
    };

    return { preFavorite, irFilter };
}
