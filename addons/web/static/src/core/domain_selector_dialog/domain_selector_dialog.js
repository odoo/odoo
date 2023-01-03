/** @odoo-module **/

import { Dialog } from "../dialog/dialog";
import { DomainSelector } from "../domain_selector/domain_selector";
import { _t } from "../l10n/translation";

import { Component, useState } from "@odoo/owl";

export class DomainSelectorDialog extends Component {
    setup() {
        this.state = useState({
            value: this.props.initialValue,
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
            value: this.state.value,
            update: (value) => {
                this.state.value = value;
            },
        };
    }

    async onSave() {
        await this.props.onSelected(this.state.value);
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
    className: { type: String, optional: true },
    resModel: String,
    readonly: { type: Boolean, optional: true },
    isDebugMode: { type: Boolean, optional: true },
    defaultLeafValue: { type: Array, optional: true },
    initialValue: { type: String, optional: true },
    onSelected: { type: Function, optional: true },
};
DomainSelectorDialog.defaultProps = {
    initialValue: "",
    onSelected: () => {},
    readonly: true,
    isDebugMode: false,
};
