import { patch } from "@web/core/utils/patch";

import { components } from "@odoo/o-spreadsheet";

const { ChartFigure, FigureComponent } = components;

patch(ChartFigure.prototype, {
    onDoubleClick() {
        // Do nothing. We don't want to open the chart side-panel.
    },
});

patch(FigureComponent.prototype, {
    openContextMenu() {
        // Do nothing. We don't want to open the menu
    },
});
