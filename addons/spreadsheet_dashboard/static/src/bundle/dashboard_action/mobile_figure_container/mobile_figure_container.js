import * as spreadsheet from "@odoo/o-spreadsheet";

import { Component, useSubEnv } from "@odoo/owl";
const { registries, stores } = spreadsheet;
const { figureRegistry } = registries;
const { ModelStore, useStoreProvider } = stores;

const EMPTY_FIGURE = { tag: "empty" };

export class MobileFigureContainer extends Component {
    static template = "documents_spreadsheet.MobileFigureContainer";
    static props = {
        spreadsheetModel: Object,
    };

    setup() {
        const stores = useStoreProvider();
        stores.inject(ModelStore, this.props.spreadsheetModel);
        useSubEnv({
            model: this.props.spreadsheetModel,
            isDashboard: () => this.props.spreadsheetModel.getters.isDashboard(),
            openSidePanel: () => {},
        });
    }

    get figureRows() {
        const sheetId = this.props.spreadsheetModel.getters.getActiveSheetId();
        const sortedFigures = this.props.spreadsheetModel.getters
            .getFigures(sheetId)
            .sort((f1, f2) => (this.isBefore(f1, f2) ? -1 : 1));

        const figureRows = [];
        for (let i = 0; i < sortedFigures.length; i++) {
            const figure = sortedFigures[i];
            const nextFigure = sortedFigures[i + 1];
            if (this.isScorecard(figure) && nextFigure && this.isScorecard(nextFigure)) {
                figureRows.push([figure, nextFigure]);
                i++;
            } else if (this.isScorecard(figure)) {
                figureRows.push([figure, EMPTY_FIGURE]);
            } else {
                figureRows.push([figure]);
            }
        }
        return figureRows;
    }

    getFigureComponent(figure) {
        return figureRegistry.get(figure.tag).Component;
    }

    isBefore(f1, f2) {
        const sheetId = this.props.spreadsheetModel.getters.getActiveSheetId();
        const fig1 = this.props.spreadsheetModel.getters.getFigureUI(sheetId, f1);
        const fig2 = this.props.spreadsheetModel.getters.getFigureUI(sheetId, f2);
        return fig1.x < fig2.x ? fig1.y < fig2.y : fig1.y < fig2.y;
    }

    isScorecard(figure) {
        if (figure.tag !== "chart") {
            return false;
        }
        const chartId = this.props.spreadsheetModel.getters.getChartIdFromFigureId(figure.id);
        const definition = this.props.spreadsheetModel.getters.getChartDefinition(chartId);
        return definition.type === "scorecard";
    }
}
