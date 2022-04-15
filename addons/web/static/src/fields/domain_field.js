/** @odoo-module **/

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { CharField } from "./char_field";
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
    }

    onButtonClick() {
        const context = this.props.record.getFieldContext(this.props.name);
        this.dialog.add(SelectCreateDialog, {
            title: this.env._t("Selected records"),
            noCreate: true,
            multiSelect: false,
            resModel: this.getResModel(this.props),
            domain: this.getDomain(this.props.value).toList(context) || [],
            context: context || {},
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

    getResModel(props) {
        if (props.record.fieldNames.includes(props.model)) {
            return props.record.data[props.model];
        }
        return props.model;
    }
    getDomain(value) {
        return new Domain(value || "[]");
    }
    async loadCount(props) {
        if (!this.getResModel(props)) {
            Object.assign(this.state, {
                recordCount: 0,
                isValid: true,
            });
        }

        try {
            this.state.recordCount = null;
            const context = props.record.getFieldContext(props.name);
            Object.assign(this.state, {
                recordCount: await this.orm.silent.call(
                    this.getResModel(props),
                    "search_count",
                    [this.getDomain(props.value).toList(context)],
                    { context }
                ),
                isValid: true,
            });
        } catch (_e) {
            // WOWL TODO: rethrow error when not the expected type
            Object.assign(this.state, {
                recordCount: 0,
                isValid: false,
            });
        }
    }

    update(domain, isDebugEdited) {
        this.isDebugEdited = isDebugEdited;
        return this.props.update(domain);
    }
}

DomainField.template = "web.DomainField";
DomainField.props = {
    ...standardFieldProps,
    model: { type: String, optional: true },
};
DomainField.components = {
    CharField,
    DomainSelector,
};
DomainField.supportedTypes = ["char"];
DomainField.isEmpty = () => false;
DomainField.extractProps = (fieldName, record, attrs) => {
    return {
        model: attrs.options.model,
    };
};

registry.category("fields").add("domain", DomainField);
