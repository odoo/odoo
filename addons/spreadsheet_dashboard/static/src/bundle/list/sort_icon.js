import { registries, constants, getCaretUpSvg, getCaretDownSvg } from "@odoo/o-spreadsheet";

const { iconsOnCellRegistry } = registries;
const { GRID_ICON_EDGE_LENGTH, GRID_ICON_MARGIN } = constants;

iconsOnCellRegistry.add("list_dashboard_sorting", (getters, position) => {
    if (!getters.isDashboard() || !getters.isSortableListHeader(position)) {
        return undefined;
    }
    const sortDirection = getters.getListSortDirection(position);
    if (sortDirection !== "asc" && sortDirection !== "desc") {
        return undefined;
    }
    const cellStyle = getters.getCellComputedStyle(position);
    return {
        type: `list_dashboard_sorting_${sortDirection}`,
        priority: 5,
        horizontalAlign: "right",
        size: GRID_ICON_EDGE_LENGTH,
        margin: GRID_ICON_MARGIN,
        svg: sortDirection === "asc" ? getCaretUpSvg(cellStyle) : getCaretDownSvg(cellStyle),
        position,
        onClick: undefined, // click is managed by ClickableCellSortIcon
    };
});
