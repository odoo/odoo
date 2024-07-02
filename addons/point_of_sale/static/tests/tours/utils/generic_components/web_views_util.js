export const List = {
    rowTrigger: (searchPattern) => `table.o_list_table tbody tr:contains("${searchPattern}")`,
    clickRow: (searchPattern) => ({
        trigger: `${List.rowTrigger(searchPattern)} td:second-child`,
    }),
    act: (action, ...searchPatterns) => [
        ...searchPatterns.map((searchPattern) => ({
            trigger: `${List.rowTrigger(searchPattern)} td:first-child input[type="checkbox"]`,
        })),
        {
            trigger: "div.o_control_panel_main button i.fa-cog",
        },
        {
            trigger: `span.dropdown-item:contains('${action}')`,
        },
    ],
};

export const Searchbar = {
    filterIs: (filter) => ({
        trigger: `div.o_searchview_facet:contains("${filter}")`,
    }),
};

// const highlightRowByColumnHeaderValue = (tableId, headerValue, cellValue) => {
//     const table = document.getElementById(tableId);
//     const headers = Array.from(table.querySelectorAll("thead th"));
//     const rows = Array.from(table.querySelectorAll("tbody tr"));
//     const columnIndex = headers.findIndex((header) => header.textContent === headerValue);
//     return columnIndex !== -1
//         ? rows.find(
//               (row) =>
//                   Array.from(row.querySelectorAll("td"))[columnIndex]?.textContent === cellValue
//           )
//         : null;
// };
