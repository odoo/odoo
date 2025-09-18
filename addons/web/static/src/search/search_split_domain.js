// @ts-check

/** @module @web/search/search_split_domain - Domain-splitting logic that decomposes compound filters into individual search items */

/**
 * Extracted domain-splitting logic for SearchModel.
 *
 * Receives the SearchModel instance as first argument (delegation pattern),
 * preserving subclass polymorphism for all internal method calls.
 */

import { domainFromTree } from "@web/components/tree_editor/domain_from_tree";
import { makeContext } from "@web/core/context";
/** @import { SearchModel } from "@web/search/search_model" */

/**
 * Split a domain into individual filter conditions and add them to the search.
 *
 * Decomposes a top-level "&"-connected domain into its children, creates
 * invisible filter search items for each, and optionally replaces an
 * existing query group (preserving its position and group-by settings).
 *
 * @param {SearchModel} searchModel - the SearchModel instance
 * @param {string} domain - the domain expression to split
 * @param {number} [groupId] - optional query group to replace
 */
export async function splitAndAddDomain(searchModel, domain, groupId) {
    const group = groupId
        ? searchModel._getGroups().find((g) => g.id === groupId)
        : null;
    let context;
    if (group) {
        const contexts = [];
        for (const activeItem of group.activeItems) {
            const ctx = searchModel._getSearchItemContext(activeItem);
            if (ctx) {
                contexts.push(ctx);
            }
        }
        context = makeContext(contexts);
    }

    const tree = await searchModel.treeProcessor.treeFromDomain(
        searchModel.resModel,
        domain,
        !searchModel.isDebugMode,
    );
    const trees =
        !tree.negate &&
        tree.type === "connector" &&
        tree.value === "&" &&
        tree.children.length > 0
            ? tree.children
            : [tree];
    const promises = trees.map(async (tree) => {
        const [description, tooltip] = await Promise.all([
            searchModel.treeProcessor.getDomainTreeDescription(
                searchModel.resModel,
                tree,
            ),
            searchModel.treeProcessor.getDomainTreeTooltip(searchModel.resModel, tree),
        ]);
        const preFilter = {
            description,
            tooltip,
            domain: domainFromTree(tree),
            invisible: "True",
            type: "filter",
        };
        if (context) {
            preFilter.context = context;
        }
        return preFilter;
    });

    const preFilters = await Promise.all(promises);

    searchModel.blockNotification = true;

    let queryItemIndex;
    if (group) {
        const firstActiveItem = group.activeItems[0];
        const firstSearchItem = searchModel.searchItems[firstActiveItem.searchItemId];
        queryItemIndex = searchModel.query.findIndex(
            (queryElem) => queryElem.searchItemId === firstActiveItem.searchItemId,
        );
        const { type } = firstSearchItem;
        if (type === "favorite") {
            const activeItemGroupBys =
                searchModel._getSearchItemGroupBys(firstActiveItem);
            let createNewGroupBys = Boolean(activeItemGroupBys.length);
            if (
                createNewGroupBys &&
                searchModel.defaultGroupBy &&
                searchModel.env.config.viewType === "kanban"
            ) {
                const currentGroupBy = searchModel._getGroupBy({
                    fallbackOnDefault: false,
                });
                if (
                    JSON.stringify(currentGroupBy) ===
                    JSON.stringify(searchModel.defaultGroupBy)
                ) {
                    createNewGroupBys = false;
                }
            }
            if (createNewGroupBys) {
                for (const activeItemGroupBy of activeItemGroupBys) {
                    const [fieldName, interval] = activeItemGroupBy.split(":");
                    searchModel.createNewGroupBy(fieldName, {
                        interval,
                        invisible: true,
                    });
                }
                const index = searchModel.query.length - activeItemGroupBys.length;
                searchModel.query = [
                    ...searchModel.query.slice(index),
                    ...searchModel.query.slice(0, index),
                ];
            }
        }
        searchModel.deactivateGroup(groupId);
    }

    const queryLength = searchModel.query.length;
    for (const preFilter of preFilters) {
        searchModel.createNewFilters([preFilter]);
    }
    const queryElems = searchModel.query.slice(queryLength);

    if (queryItemIndex !== undefined) {
        searchModel.query = [
            ...searchModel.query.slice(0, queryItemIndex),
            ...queryElems,
            ...searchModel.query.slice(queryItemIndex, queryLength),
        ];
    }

    searchModel.blockNotification = false;

    searchModel._notify();
}
