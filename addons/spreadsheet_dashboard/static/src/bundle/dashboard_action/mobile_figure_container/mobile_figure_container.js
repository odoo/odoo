/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";

import { Component, useSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
const { registries } = spreadsheet;
const { figureRegistry } = registries;

export class MobileFigureContainer extends Component {
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

    async navigateToOdooMenu(figureId) {
        const menu = this.props.spreadsheetModel.getters.getChartOdooMenu(figureId);
        if (!menu) {
            this.notificationService.add(
                _t(
                    "This chart is not linked to any menu. Please link it to a menu to enable navigation."
                ),
                { type: "warning" }
            );
            return;
        }
        if (!menu.actionID) {
            this.notificationService.add(
                _t(
                    "The menu linked to this chart does not have a corresponding action. Please link the chart to another menu."
                ),
                { type: "danger" }
            );
            return;
        }
        await this.actionService.doAction(menu.actionID);
    }
}

MobileFigureContainer.template = "documents_spreadsheet.MobileFigureContainer";

MobileFigureContainer.props = {
    spreadsheetModel: Object,
};
