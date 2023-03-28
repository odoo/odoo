/** @odoo-module **/

import { _t } from "../l10n/translation";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "../dialog/dialog";
import { DomainSelector } from "../domain_selector/domain_selector";

export class DomainSelectorDialog extends Component {
    setup() {
        this.state = useState({
            domain: this.props.domain,
        });
    }

    get dialogTitle() {
        return _t("Domain");
    }

    get domainSelectorProps() {
        return {
            className: this.props.className,
            resModel: this.props.resModel,
            readonly: this.props.readonly,
            isDebugMode: this.props.isDebugMode,
            defaultLeafValue: this.props.defaultLeafValue,
            value: this.state.domain,
            update: (domain) => {
                this.state.domain = domain;
            },
        };
    }

    async onConfirm() {
        await this.props.onConfirm(this.state.domain);
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
    defaultLeafValue: { type: Array, optional: true },
    domain: { type: String, optional: true },
    isDebugMode: { type: Boolean, optional: true },
    readonly: { type: Boolean, optional: true },
    text: { type: String, optional: true },
};
DomainSelectorDialog.defaultProps = {
    domain: "[]",
    isDebugMode: false,
    readonly: false,
};
