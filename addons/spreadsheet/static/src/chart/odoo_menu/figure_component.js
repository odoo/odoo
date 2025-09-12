/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";
import { navigateToOdooMenu } from "@spreadsheet/helpers/helpers";

patch(spreadsheet.components.FigureComponent.prototype, {
    setup() {
        super.setup();
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    get hasOdooMenu() {
        return this.env.model.getters.getChartOdooMenu(this.props.figure.id) !== undefined;
    },
    async onClick() {
        if (this.hasOdooMenu) {
            await navigateToOdooMenu({
                figureId: this.props.figure.id,
                model: this.env.model,
                notificationService: this.notificationService,
                actionService: this.actionService,
            });
        }
    },
});
