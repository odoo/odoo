/** @odoo-module **/

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { standardFieldProps } from "../standard_field_props";

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

export class DomainField extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.state = useState({
            recordCount: null,
            isValid: true,
        });
        this.addDialog = useOwnedDialogs();

        this.displayedDomain = null;
        this.isDebugEdited = false;

        onWillStart(() => {
            this.displayedDomain = this.props.value;
            this.loadCount(this.props);
        });
        onWillUpdateProps((nextProps) => {
            this.isDebugEdited = this.isDebugEdited && this.props.readonly === nextProps.readonly;
            if (!this.isDebugEdited) {
                this.displayedDomain = nextProps.value;
                this.loadCount(nextProps);
            }
        });

        useBus(this.env.bus, "RELATIONAL_MODEL:NEED_LOCAL_CHANGES", async (ev) => {
            if (this.isDebugEdited) {
                const props = this.props;
                const prom = this.quickValidityCheck(props);
                ev.detail.proms.push(prom);
                prom.then((isValid) => {
                    if (isValid) {
                        this.isDebugEdited = false; // will allow the count to be loaded if needed
                    } else {
                        this.state.isValid = false;
                        this.state.recordCount = 0;
                        this.props.record.setInvalidField(props.name);
                    }
                });
            }
        });
    }

    async quickValidityCheck(p) {
        const model = this.getResModel(p);
        if (!model) {
            return false;
        }
        try {
            const domain = this.getDomain(p.value).toList(this.getContext(p));
            return this.rpc("/web/domain/validate", { model, domain });
        } catch (_) {
            return false;
        }
    }

    getContext(p) {
        return p.record.getFieldContext(p.name);
    }
    getResModel(p) {
        let resModel = p.resModel;
        if (p.record.fieldNames.includes(resModel)) {
            resModel = p.record.data[resModel];
        }
        return resModel;
    }

    onButtonClick() {
        this.addDialog(
            SelectCreateDialog,
            {
                title: this.env._t("Selected records"),
                noCreate: true,
                multiSelect: false,
                resModel: this.getResModel(this.props),
                domain: this.getDomain(this.props.value).toList(this.getContext(this.props)) || [],
                context: this.getContext(this.props) || {},
            },
            {
                // The counter is reloaded "on close" because some modal allows to modify data that can impact the counter
                onClose: () => this.loadCount(this.props),
            }
        );
    }
    get isValidDomain() {
        try {
            this.getDomain(this.props.value).toList();
            return true;
        } catch (_e) {
            // WOWL TODO: rethrow error when not the expected type
            return false;
        }
    }

    getDomain(value) {
        return new Domain(value || "[]");
    }
    async loadCount(props) {
        if (!this.getResModel(props)) {
            Object.assign(this.state, { recordCount: 0, isValid: true });
        }

        let recordCount;
        try {
            const domain = this.getDomain(props.value).toList(this.getContext(props));
            recordCount = await this.orm.silent.call(
                this.getResModel(props),
                "search_count",
                [domain],
                { context: this.getContext(props) }
            );
        } catch (_e) {
            // WOWL TODO: rethrow error when not the expected type
            Object.assign(this.state, { recordCount: 0, isValid: false });
            return;
        }
        Object.assign(this.state, { recordCount, isValid: true });
    }

    update(domain, isDebugEdited) {
        this.isDebugEdited = isDebugEdited;
        return this.props.update(domain);
    }

    onEditDialogBtnClick() {
        this.addDialog(DomainSelectorDialog, {
            resModel: this.getResModel(this.props),
            initialValue: this.props.value || "[]",
            readonly: this.props.readonly,
            isDebugMode: !!this.env.debug,
            onSelected: this.props.update,
        });
    }
}

DomainField.template = "web.DomainField";
DomainField.components = {
    DomainSelector,
};
DomainField.props = {
    ...standardFieldProps,
    editInDialog: { type: Boolean, optional: true },
    resModel: { type: String, optional: true },
};
DomainField.defaultProps = {
    editInDialog: false,
};

DomainField.displayName = _lt("Domain");
DomainField.supportedTypes = ["char"];

DomainField.isEmpty = () => false;
DomainField.extractProps = ({ attrs }) => {
    return {
        editInDialog: attrs.options.in_dialog,
        resModel: attrs.options.model,
    };
};

registry.category("fields").add("domain", DomainField);
