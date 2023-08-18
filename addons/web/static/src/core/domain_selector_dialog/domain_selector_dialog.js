/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useRef, useState } from "@odoo/owl";
import { Dialog } from "../dialog/dialog";
import { Domain } from "@web/core/domain";
import { DomainSelector } from "../domain_selector/domain_selector";
import { useService } from "../utils/hooks";

export class DomainSelectorDialog extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.user = useService("user");
        this.state = useState({ domain: this.props.domain });
        this.confirmButtonRef = useRef("confirm");
    }

    get confirmButtonText() {
        return this.props.confirmButtonText || _t("Confirm");
    }

    get dialogTitle() {
        return this.props.title || _t("Domain");
    }

    get disabled() {
        if (this.props.disableConfirmButton) {
            return this.props.disableConfirmButton(this.state.domain);
        }
        return false;
    }

    get discardButtonText() {
        return this.props.discardButtonText || _t("Discard");
    }

    get domainSelectorProps() {
        return {
            className: this.props.className,
            resModel: this.props.resModel,
            readonly: this.props.readonly,
            isDebugMode: this.props.isDebugMode,
            defaultConnector: this.props.defaultConnector,
            defaultLeafValue: this.props.defaultLeafValue,
            domain: this.state.domain,
            update: (domain) => {
                this.state.domain = domain;
            },
        };
    }

    async onConfirm() {
        this.confirmButtonRef.el.disabled = true;
        let domain;
        let isValid;
        try {
            const evalContext = { ...this.user.context, ...this.props.context };
            domain = new Domain(this.state.domain).toList(evalContext);
        } catch {
            isValid = false;
        }
        if (isValid === undefined) {
            isValid = await this.rpc("/web/domain/validate", {
                model: this.props.resModel,
                domain,
            });
        }
        if (!isValid) {
            if (this.confirmButtonRef.el) {
                this.confirmButtonRef.el.disabled = false;
            }
            this.notification.add(_t("Domain is invalid. Please correct it"), {
                type: "danger",
            });
            return;
        }
        this.props.onConfirm(this.state.domain);
        this.props.close();
    }

    onDiscard() {
        this.props.close();
    }
}
DomainSelectorDialog.template = "web.DomainSelectorDialog";
DomainSelectorDialog.components = {
    Dialog,
    DomainSelector,
};
DomainSelectorDialog.props = {
    close: Function,
    onConfirm: Function,
    resModel: String,
    className: { type: String, optional: true },
    defaultConnector: { type: [{ value: "&" }, { value: "|" }], optional: true },
    defaultLeafValue: { type: Array, optional: true },
    domain: String,
    isDebugMode: { type: Boolean, optional: true },
    readonly: { type: Boolean, optional: true },
    text: { type: String, optional: true },
    confirmButtonText: { type: String, optional: true },
    disableConfirmButton: { type: Function, optional: true },
    discardButtonText: { type: String, optional: true },
    title: { type: String, optional: true },
    context: { type: Object, optional: true },
};
DomainSelectorDialog.defaultProps = {
    isDebugMode: false,
    readonly: false,
    context: {},
};
