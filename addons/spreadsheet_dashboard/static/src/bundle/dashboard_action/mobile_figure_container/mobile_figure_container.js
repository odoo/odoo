/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";

import { Component, useSubEnv } from "@odoo/owl";
import { navigateToOdooMenu } from "@spreadsheet/helpers/helpers";
import { useService } from "@web/core/utils/hooks";
const { registries } = spreadsheet;
const { figureRegistry } = registries;

export class MobileFigureContainer extends Component {
    static template = "documents_spreadsheet.MobileFigureContainer";
    static props = {
        spreadsheetModel: Object,
    };

    setup() {
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        useSubEnv({
            model: this.props.spreadsheetModel,
            isDashboard: () => this.props.spreadsheetModel.getters.isDashboard(),
            openSidePanel: () => {},
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
            }));
    }

    getFigureComponent(figure) {
        return figureRegistry.get(figure.tag).Component;
    }

    isBefore(f1, f2) {
        // TODO be smarter
        return f1.x < f2.x ? f1.y < f2.y : f1.y < f2.y;
    }

    hasOdooMenu(figureId) {
        return this.props.spreadsheetModel.getters.getChartOdooMenu(figureId) !== undefined;
    }

    async onClick(figureId) {
        if (this.hasOdooMenu(figureId)) {
            await navigateToOdooMenu({
                figureId,
                model: this.props.spreadsheetModel,
                notificationService: this.notificationService,
                actionService: this.actionService,
            });
        }
    }
}
