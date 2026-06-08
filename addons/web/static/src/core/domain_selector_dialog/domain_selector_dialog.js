import { useRef } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { Component, props, proxy, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Domain } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class DomainSelectorDialog extends Component {
    static template = "web.DomainSelectorDialog";
    static components = {
        Dialog,
        DomainSelector,
    };
    props = props({
        close: t.function(),
        onConfirm: t.function(),
        resModel: t.string(),
        className: t.string().optional(),
        defaultConnector: t.selection(["&", "|"]).optional(),
        domain: t.string(),
        isDebugMode: t.boolean().optional(false),
        readonly: t.boolean().optional(false),
        text: t.string().optional(),
        confirmButtonText: t.string().optional(),
        disableConfirmButton: t.function().optional(),
        discardButtonText: t.string().optional(),
        title: t.string().optional(),
        context: t.object().optional({}),
    });

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = proxy({ domain: this.props.domain });
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
            const evalContext = { ...user.context, ...this.props.context };
            domain = new Domain(this.state.domain).toList(evalContext);
        } catch {
            isValid = false;
        }
        if (isValid === undefined) {
            isValid = await rpc("/web/domain/validate", {
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
