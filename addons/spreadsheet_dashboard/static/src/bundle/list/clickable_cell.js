import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "@spreadsheet/list/list_actions";
import { registries, components, readonlyAllowedCommands } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { clickableCellRegistry } = registries;
const { ClickableCellSortIcon } = components;

readonlyAllowedCommands.add("UPDATE_ODOO_LIST");

clickableCellRegistry.add("list", {
    condition: SEE_RECORD_LIST_VISIBLE,
    execute: SEE_RECORD_LIST,
    sequence: 10,
    title: _t("Open record"),
});

function sortList(env, position, direction) {
    const field = env.model.getters.getListFieldFromPosition(position);
    if (!field) {
        return;
    }
    const listId = env.model.getters.getListIdFromPosition(position);
    const definition = env.model.getters.getListModelDefinition(listId);
    const orderBy =
        direction === "none"
            ? []
            : [
                  { name: field.name, asc: direction === "asc" },
                  ...definition.searchParams.orderBy.filter(
                      (orderBy) => orderBy.name !== field.name
                  ),
              ];
    env.model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...definition,
            searchParams: {
                ...definition.searchParams,
                orderBy,
            },
        },
    });
}

clickableCellRegistry.add("dashboard_list_sorting", {
    condition: (position, getters) =>
        getters.isDashboard() && getters.isSortableListHeader(position),
    execute: (position, env) => {
        sortList(env, position, getNextSortDirection(env.model.getters, position));
    },
    component: ClickableCellSortIcon,
    componentProps: (position, getters) => ({
        position,
        sortDirection: getters.getListSortDirection(position),
    }),
    sequence: 2,
});

const NEXT_SORT_DIRECTION = { asc: "desc", desc: "none", none: "asc" };

function getNextSortDirection(getters, position) {
    return NEXT_SORT_DIRECTION[getters.getListSortDirection(position)];
}
