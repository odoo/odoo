/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

export class MrpWorkcenterDialog extends ConfirmationDialog {
    static template = "mrp_workorder.MrpWorkcenterDialog";
    static props = {
        ...ConfirmationDialog.props,
        body: { type: String, optional: true },
        workcenters: { type: Array, optional: true },
        disabled: { type: Array, optional: true },
        active: { type: Array, optional: true },
        radioMode: { type: Boolean, default: false, optional: true },
        loadWorkcenters: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.ormService = useService("orm");
        this.menu = useService("menu");
        this.notification = useService("notification");
        this.workcenters = this.props.workcenters || [];
        this.state = useState({
            activeWorkcenters: this.props.active ? [...this.props.active] : [],
        });
        this.isDisplayStandalone = isDisplayStandalone();

        onWillStart(async () => {
            if (!this.workcenters.length) {
                this.workcenters = await this.props.loadWorkcenters();
            }
        });
    }

    get appName() {
        return encodeURIComponent(this.menu.getCurrentApp()?.name || _t("Shop Floor"));
    }

    get active() {
        return this.state.activeWorkcenters.includes(this.workcenter.id);
    }

    get disabled() {
        if (!this.props.disabled) {
            return false;
        }
        return this.props.disabled.includes(this.workcenter.id);
    }

    selectWorkcenter(workcenter) {
        if (this.props.radioMode) {
            this.state.activeWorkcenters = [workcenter.id];
        } else if (this.state.activeWorkcenters.includes(workcenter.id)) {
            this.state.activeWorkcenters = this.state.activeWorkcenters.filter(
                (id) => id !== workcenter.id
            );
        } else {
            this.state.activeWorkcenters.push(workcenter.id);
        }
    }

    confirm() {
        this.props.confirm(
            this.state.activeWorkcenters.reduce((acc, id) => {
                const res = this.workcenters.find((wc) => wc.id === id);
                return res ? [...acc, res] : acc;
            }, [])
        );
        this.props.close();
    }
}
