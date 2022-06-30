/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useChildRef, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "../standard_field_props";
import { Domain } from "@web/core/domain";
import { Many2XAutocomplete, useOpenMany2XRecord } from "@web/views/fields/relational_utils";

const { Component, onWillUpdateProps, useState } = owl;

class CreateConfirmationDialog extends Component {
    get title() {
        return sprintf(this.env._t("New: %s"), this.props.name);
    }

    async onCreate() {
        await this.props.create();
        this.props.close();
    }
}
CreateConfirmationDialog.components = { Dialog };
CreateConfirmationDialog.template = "web.Many2OneField.CreateConfirmationDialog";

function m2oTupleFromData(data) {
    const id = data.id;
    let name;
    if ("display_name" in data) {
        name = data.display_name;
    } else {
        let _name = data.name;
        name = Array.isArray(_name) ? _name[1] : _name;
    }
    return [id, name];
}

export class Many2OneField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.autocompleteContainerRef = useChildRef();
        this.addDialog = useOwnedDialogs();

        this.focusInput = () => {
            this.autocompleteContainerRef.el.querySelector("input").focus();
        };

        const computeActiveActions = (props) => {
            this.state.activeActions = {
                canCreate: props.canCreate,
                canCreateEdit: props.canCreateEdit,
                canWrite: props.canWrite,
            };
        };

        this.state = useState({
            isFloating: !this.props.value,
        });
        computeActiveActions(this.props);

        this.openMany2X = useOpenMany2XRecord({
            resModel: this.props.relation,
            activeActions: this.state.activeActions,
            isToMany: false,
            onRecordSaved: async (record) => {
                await this.props.record.load();
                await this.props.update(m2oTupleFromData(record.data));
                if (this.props.record.model.root.id !== this.props.record.id) {
                    this.props.record.switchMode("readonly");
                }
            },
            onClose: () => this.focusInput(),
            fieldString: this.props.string,
        });

        this.update = (value, params = {}) => {
            if (value) {
                value = m2oTupleFromData(value[0]);
            }
            if (!value && !this.updateOnEmpty) {
                return;
            }
            this.state.isFloating = false;
            return this.props.update(value);
        };

        if (this.props.canQuickCreate) {
            this.quickCreate = (name, params = {}) => {
                if (params.triggeredOnBlur) {
                    return this.openConfirmationDialog(name);
                }
                return this.props.update([false, name]);
            };
        }

        this.setFloating = (bool) => {
            this.state.isFloating = bool;
        };

        onWillUpdateProps(async (nextProps) => {
            this.state.isFloating = !nextProps.value;
            computeActiveActions(nextProps);
        });
    }

    get hasExternalButton() {
        return this.props.canOpen && !!this.props.value && !this.state.isFloating;
    }
    get displayName() {
        return this.props.value ? this.props.value[1].split("\n")[0] : "";
    }
    get extraLines() {
        return this.props.value
            ? this.props.value[1]
                  .split("\n")
                  .map((line) => line.trim())
                  .slice(1)
            : [];
    }
    get resId() {
        return this.props.value && this.props.value[0];
    }
    get updateOnEmpty() {
        return true;
    }

    getDomain() {
        return this.props.getDomain().toList(this.props.getContext());
    }
    async openAction() {
        const action = await this.orm.call(
            this.props.relation,
            "get_formview_action",
            [[this.resId]],
            { context: this.props.getContext() }
        );
        await this.action.doAction(action);
    }
    async openDialog(resId) {
        return this.openMany2X({ resId, context: this.props.getContext() });
    }

    async openConfirmationDialog(request) {
        return new Promise((resolve, reject) => {
            this.addDialog(CreateConfirmationDialog, {
                value: request,
                name: this.props.string,
                create: async () => {
                    try {
                        await this.quickCreate(request);
                        resolve();
                    } catch (e) {
                        reject(e);
                    }
                },
            });
        });
    }

    onClick(ev) {
        if (this.props.canOpen && this.props.readonly) {
            ev.stopPropagation();
            this.openAction();
        }
    }
    onExternalBtnClick() {
        this.openDialog(this.resId);
    }
}

Many2OneField.SEARCH_MORE_LIMIT = 320;

Many2OneField.template = "web.Many2OneField";
Many2OneField.components = {
    Many2XAutocomplete,
};
Many2OneField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
    canOpen: { type: Boolean, optional: true },
    canCreate: { type: Boolean, optional: true },
    canWrite: { type: Boolean, optional: true },
    canQuickCreate: { type: Boolean, optional: true },
    canCreateEdit: { type: Boolean, optional: true },
    createNameField: { type: String, optional: true },
    searchLimit: { type: Number, optional: true },
    relation: String,
    string: { type: String, optional: true },
    getContext: { type: Function, optional: true },
    getDomain: { type: Function, optional: true },
};
Many2OneField.defaultProps = {
    canOpen: true,
    canCreate: true,
    canWrite: true,
    canQuickCreate: true,
    canCreateEdit: true,
    createNameField: "name",
    searchLimit: 7,
    string: "",
    getContext: () => ({}),
    getDomain: () => new Domain(),
};

Many2OneField.displayName = _lt("Many2one");
Many2OneField.supportedTypes = ["many2one"];

Many2OneField.extractProps = (fieldName, record, attrs) => {
    const noOpen = Boolean(attrs.options.no_open);
    const noCreate = Boolean(attrs.options.no_create);
    const canCreate = attrs.can_create && Boolean(JSON.parse(attrs.can_create)) && !noCreate;
    const canWrite = attrs.can_write && Boolean(JSON.parse(attrs.can_write));
    const noQuickCreate = Boolean(attrs.options.no_quick_create);
    const noCreateEdit = Boolean(attrs.options.no_create_edit);

    return {
        placeholder: attrs.placeholder,
        canOpen: !noOpen,
        canCreate,
        canWrite,
        canQuickCreate: canCreate && !noQuickCreate,
        canCreateEdit: canCreate && !noCreateEdit,
        relation: record.fields[fieldName].relation,
        string: attrs.string || record.fields[fieldName].string,
        getContext: () => record.getFieldContext(fieldName),
        getDomain: () => record.getFieldDomain(fieldName),
        createNameField: attrs.options.create_name_field,
    };
};

registry.category("fields").add("many2one", Many2OneField);

export class ListMany2OneField extends Many2OneField {
    get updateOnEmpty() {
        return false;
    }
}

registry.category("fields").add("list.many2one", ListMany2OneField); // TODO WOWL: link isn't clickable in lists
