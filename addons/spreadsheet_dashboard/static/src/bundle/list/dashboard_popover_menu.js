import { helpers, registries, readonlyAllowedCommands, constants } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { dashboardGridMenuRegistry } = registries;
const { ACTION_COLOR } = constants;
const { highlightOnMenuHover, mergeContiguousZones, positionToZone } = helpers;

readonlyAllowedCommands.add("UPDATE_ODOO_LIST");

function isListSortingVisible(getters, position) {
    const listId = getters.getListIdFromPosition(position);
    if (!listId) {
        return false;
    }
    const dataSource = getters.getListDataSource(listId);
    return dataSource.isMetaDataLoaded() && getters.getListFieldFromPosition(position)?.sortable;
}

function sortList(env, position, direction) {
    const field = env.model.getters.getListFieldFromPosition(position);
    if (!field) {
        return;
    }
    const listId = env.model.getters.getListIdFromPosition(position);
    const definition = env.model.getters.getListModelDefinition(listId);
    env.model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...definition,
            searchParams: {
                ...definition.searchParams,
                orderBy: [
                    { name: field.name, asc: direction === "asc" },
                    ...definition.searchParams.orderBy.filter(
                        (orderBy) => orderBy.name !== field.name
                    ),
                ],
            },
        },
    });
}

function getListSortingHighlights(env, startingPosition) {
    const positions = env.model.getters
        .getVisibleCellPositions()
        .filter(
            (position) =>
                position.col === startingPosition.col &&
                isListSortingVisible(env.model.getters, position)
        );
    const zones = mergeContiguousZones(positions.map(positionToZone));
    const highlights = zones.map((zone) => ({
        zone,
        color: ACTION_COLOR,
        sheetId: startingPosition.sheetId,
    }));
    return highlights;
}

function isListSortingActive(env, position, direction) {
    const field = env.model.getters.getListFieldFromPosition(position);
    const listId = env.model.getters.getListIdFromPosition(position);
    const orderBy = env.model.getters.getListDefinition(listId).orderBy[0];
    return (
        field &&
        orderBy?.name === field.name &&
        (orderBy.asc ? direction === "asc" : direction === "desc")
    );
}

dashboardGridMenuRegistry
    .add("sort_list_ascending", {
        name: _t("Sort ascending (0 ⟶ 100)"),
        icon: "o-spreadsheet-Icon.SORT_ASCENDING_NUMERIC",
        iconColor: (env, position) =>
            isListSortingActive(env, position, "asc") ? ACTION_COLOR : "",
        isVisible: isListSortingVisible,
        execute(env, position) {
            sortList(env, position, "asc");
        },
        onStartHover: (env, position) => {
            const highlights = getListSortingHighlights(env, position);
            return highlightOnMenuHover(env, { highlights });
        },
    })
    .add("sort_list_descending", {
        name: _t("Sort descending (100 ⟶ 0)"),
        icon: "o-spreadsheet-Icon.SORT_DESCENDING_NUMERIC",
        iconColor: (env, position) =>
            isListSortingActive(env, position, "desc") ? ACTION_COLOR : "",
        isVisible: isListSortingVisible,
        execute(env, position) {
            sortList(env, position, "desc");
        },
        onStartHover: (env, position) => {
            const highlights = getListSortingHighlights(env, position);
            return highlightOnMenuHover(env, { highlights });
        },
    });
