/** @odoo-module **/

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { standardFieldProps } from "./standard_field_props";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

const { Component, onWillStart, onWillUpdateProps, useState } = owl;

export class DomainField extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            recordCount: null,
            isValid: true,
        });
        this.dialog = useService("dialog");

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

        useBus(this.env.bus, "RELATIONAL_MODEL:WILL_SAVE", async (ev) => {
            if (this.isDebugEdited) {
                const prom = this.loadCount(this.props);
                ev.detail.proms.push(prom);
                await prom;
                if (!this.state.isValid) {
                    this.props.invalidate();
                }
            }
        });
    }

    onButtonClick() {
        this.dialog.add(SelectCreateDialog, {
            title: this.env._t("Selected records"),
            noCreate: true,
            multiSelect: false,
            resModel: this.props.resModel,
            domain: this.getDomain(this.props.value).toList(this.props.context) || [],
            context: this.props.context || {},
        });
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
        if (!props.resModel) {
            Object.assign(this.state, { recordCount: 0, isValid: true });
        }

        let recordCount;
        try {
            const domain = this.getDomain(props.value).toList(props.context);
            recordCount = await this.orm.silent.call(props.resModel, "search_count", [domain], {
                context: props.context,
            });
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
}

DomainField.template = "web.DomainField";
DomainField.components = {
    DomainSelector,
};
DomainField.props = {
    ...standardFieldProps,
    context: { type: Object, optional: true },
    invalidate: { type: Function, optional: true },
    resModel: { type: String, optional: true },
};
DomainField.defaultProps = {
    context: {},
    invalidate: () => {},
};

DomainField.displayName = _lt("Domain");
DomainField.supportedTypes = ["char"];

DomainField.isEmpty = () => false;
DomainField.extractProps = (fieldName, record, attrs) => {
    let resModel = attrs.options.model;
    if (record.fieldNames.includes(resModel)) {
        resModel = record.data[resModel];
    }

    return {
        context: record.getFieldContext(fieldName),
        invalidate: () => record.setInvalidField(fieldName),
        resModel,
    };
};

registry.category("fields").add("domain", DomainField);
