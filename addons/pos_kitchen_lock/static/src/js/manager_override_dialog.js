/** @odoo-module */
/* global Sha1 */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { _t } from "@web/core/l10n/translation";

export class ManagerOverrideDialog extends Component {
    static template = "pos_kitchen_lock.ManagerOverrideDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        getPayload: Function,
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({ selecting: false });
    }

    /**
     * Returns employees whose role is manager or cashier (not minimal),
     * excluding whoever is currently logged in.
     */
    get managers() {
        if (!this.pos.config.module_pos_hr) {
            return [];
        }
        const currentId = this.pos.getCashier()?.id;
        return (this.pos.models["hr.employee"] || []).filter(
            (emp) => emp._role !== "minimal" && emp.id !== currentId
        );
    }

    async selectManager(emp) {
        if (this.state.selecting) {
            return;
        }
        this.state.selecting = true;
        try {
            if (emp._pin) {
                const inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                    formatDisplayedValue: (x) => x.replace(/./g, "•"),
                    title: _t("PIN for %s", emp.name),
                });
                if (!inputPin || Sha1.hash(inputPin) !== emp._pin) {
                    this.notification.add(_t("Incorrect PIN — try again."), {
                        type: "warning",
                        title: _t("Wrong PIN"),
                    });
                    this.state.selecting = false;
                    return;
                }
            }
            this.props.getPayload(emp);
            this.props.close();
        } catch (_e) {
            this.state.selecting = false;
        }
    }

    cancel() {
        this.props.close();
    }
}
