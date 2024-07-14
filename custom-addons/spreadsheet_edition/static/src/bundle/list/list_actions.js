/** @odoo-module */

export const REINSERT_LIST_CHILDREN = (env) =>
    env.model.getters.getListIds().map((listId, index) => {
        return {
            id: `reinsert_list_${listId}`,
            name: env.model.getters.getListDisplayName(listId),
            sequence: index,
            execute: async (env) => {
                const zone = env.model.getters.getSelectedZone();
                const dataSource = await env.model.getters.getAsyncListDataSource(listId);
                const list = env.model.getters.getListDefinition(listId);
                const columns = list.columns.map((name) => ({
                    name,
                    type: dataSource.getField(name).type,
                }));
                env.getLinesNumber((linesNumber) => {
                    env.model.dispatch("RE_INSERT_ODOO_LIST", {
                        sheetId: env.model.getters.getActiveSheetId(),
                        col: zone.left,
                        row: zone.top,
                        id: listId,
                        linesNumber,
                        columns: columns,
                    });
                });
            },
        };
    });
