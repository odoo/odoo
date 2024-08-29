export const List = {
    rowTrigger: (searchPattern) => `table.o_list_table tbody tr:contains("${searchPattern}")`,
    clickRow: (searchPattern) => ({
        trigger: `${List.rowTrigger(searchPattern)} td:nth-child(2)`,
        run: "click",
    }),
};
export const Kanban = {
    trigger: (searchPattern) => `div.o_kanban_view .o_kanban_record:contains("${searchPattern}")`,
    click: (searchPattern) => ({
        trigger: Kanban.trigger(searchPattern),
        run: "click",
    }),
};
