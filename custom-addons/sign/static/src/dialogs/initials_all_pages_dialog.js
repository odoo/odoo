/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class InitialsAllPagesDialog extends Component {
    setup() {
        this.selectRef = useRef("role_select");
    }

    get currentRole() {
        return parseInt(this.selectRef.el?.value);
    }

    onAddOnceClick() {
        this.props.addInitial(this.currentRole, false);
        this.props.close();
    }

    onAddToAllPagesClick() {
        this.props.addInitial(this.currentRole, true);
        this.props.close();
    }

    get dialogProps() {
        return {
            size: "md",
            title: _t("Add Initials"),
        };
    }
}

InitialsAllPagesDialog.template = "sign.InitialsAllPagesDialog";
InitialsAllPagesDialog.components = {
    Dialog,
};

InitialsAllPagesDialog.props = {
    addInitial: Function,
    close: Function,
    roles: Object,
    responsible: Number,
};
