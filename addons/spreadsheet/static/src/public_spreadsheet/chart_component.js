import { patch } from "@web/core/utils/patch";

import { components } from "@odoo/o-spreadsheet";

const { ChartFigure, CarouselFigure, ChartMenu, FigureComponent } = components;

patch(ChartFigure.prototype, {
    onDoubleClick() {
        // Do nothing. We don't want to open the chart side-panel.
    },
});

patch(CarouselFigure.prototype, {
    onCarouselDoubleClick() {
        // Do nothing. We don't want to open the chart side-panel.
    },
    onCarouselChartDoubleClick() {
        // Do nothing. We don't want to open the chart side-panel.
    },
});

patch(FigureComponent.prototype, {
    openContextMenu() {
        // Do nothing. We don't want to open the menu
    },
});

patch(ChartMenu.prototype, {
    openContextMenu() {
        // Do nothing. We don't want to open the menu
    },
});
