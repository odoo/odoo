/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { Component, useSubEnv } = owl;
const { registries } = spreadsheet;
const { figureRegistry } = registries;

export class MobileFigureContainer extends Component {
    setup() {
        useSubEnv({
            model: this.props.spreadsheetModel,
            isDashboard: () => this.props.spreadsheetModel.getters.isDashboard(),
        });
    }

    get figures() {
        const sheetId = this.props.spreadsheetModel.getters.getActiveSheetId();
        return this.props.spreadsheetModel.getters
            .getFigures(sheetId)
            .sort((f1, f2) => (this.isBefore(f1, f2) ? -1 : 1))
            .map((figure) => ({
                ...figure,
                width: window.innerWidth,
                height: 300,
            }));
    }

    getFigureComponent(figure) {
        return figureRegistry.get(figure.tag).Component;
    }

    isBefore(f1, f2) {
        // TODO be smarter
        return f1.x < f2.x ? f1.y < f2.y : f1.y < f2.y;
    }
}

MobileFigureContainer.template = "documents_spreadsheet.MobileFigureContainer";
