/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf, escape } from "@web/core/utils/strings";
import { standardFieldProps } from "./standard_field_props";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { SelectCreateDialog } from "../views/view_dialogs/select_create_dialog";

const { Component, onWillUpdateProps, useState } = owl;

export class Many2OneField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");

        this.state = useState({
            isFloating: !this.props.value,
        });

        onWillUpdateProps(async (nextProps) => {
            this.state.isFloating = !nextProps.value;
        });
    }

    get hasExternalButton() {
        return this.props.canOpen && !!this.props.value && !this.state.isFloating;
    }
    get sources() {
        return [this.recordSource];
    }
    get recordSource() {
        return {
            placeholder: this.env._t("Loading..."),
            options: this.loadRecordSource.bind(this),
        };
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

    getDomain() {
        return this.props.record
            .getFieldDomain(this.props.name)
            .toList(this.props.record.getFieldContext(this.props.name));
    }

    async loadRecordSource(request) {
        const records = await this.orm.call(this.props.relation, "name_search", [], {
            name: request,
            args: this.getDomain(),
            operator: "ilike",
            limit: this.props.searchLimit + 1,
            context: this.props.record.getFieldContext(this.props.name),
        });

        const options = records.map((result) => ({
            value: result[0],
            label: result[1],
        }));

        // Add "Search more..." option if records count is higher than the limit
        if (this.props.searchLimit < records.length) {
            options.push({
                label: this.env._t("Search More..."),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
                action: this.onSearchMore.bind(this),
            });
        }

        if (request.length) {
            // "Quick create" option
            if (this.props.canQuickCreate && !records.some((record) => record[1] === request)) {
                options.push({
                    label: sprintf(this.env._t(`Create "%s"`), escape(request)),
                    classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
                    action: this.onCreate.bind(this),
                });
            }

            // "Create and Edit" option
            if (this.props.canCreateEdit) {
                options.push({
                    label: this.env._t(`Create and Edit...`),
                    classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
                    action: this.onCreateEdit.bind(this),
                });
            }

            // "No results" option
            if (!options.length) {
                options.push({
                    label: this.env._t("No records"),
                    classList: "o_m2o_no_result",
                    unselectable: true,
                });
            }
        } else if (!this.props.value && (this.props.canQuickCreate || this.props.canCreateEdit)) {
            // "Start typing" option
            options.push({
                label: this.env._t("Start typing..."),
                classList: "o_m2o_start_typing",
                unselectable: true,
            });
        }

        return options;
    }

    async openAction() {
        const action = await this.orm.call(
            this.props.relation,
            "get_formview_action",
            [[this.resId]],
            { context: this.props.record.getFieldContext(this.props.name) }
        );
        await this.action.doAction(action);
    }
    async openDialog(resId) {
        const viewId = await this.orm.call(this.props.relation, "get_formview_id", [[this.resId]], {
            context: this.props.record.getFieldContext(this.props.name),
        });

        this.dialog.add(FormViewDialog, {
            parent: this,
            resId,
            mode: this.props.readonly ? "readonly" : "edit",
            context: this.props.record.getFieldContext(this.props.name),
            resModel: this.props.relation,
            viewId,
            title: sprintf(
                this.env._t("Open: %s"),
                this.props.record.activeFields[this.props.name].string
            ),
        });
    }

    onSearchMore() {
        this.dialog.add(SelectCreateDialog, {
            parent: this,
            resModel: this.props.relation,
            domain: this.getDomain(),
            title: sprintf(
                this.env._t("Search: %s"),
                this.props.record.activeFields[this.props.name].string
            ),
            multiSelect: false,
            onSelected: ([resId]) => {
                this.props.update([resId]);
            },
            searchViewId: false,
        });
    }
    onCreate() {
        console.log("create");
    }
    onCreateEdit() {
        console.log("create edit");
    }

    onClick() {
        this.openAction();
    }
    onExternalBtnClick() {
        this.openDialog(this.resId);
    }
    onChange({ inputValue }) {
        if (!inputValue.length) {
            this.props.update(false);
        }
    }
    onInput({ inputValue }) {
        this.state.isFloating = !this.props.value || this.props.value[1] !== inputValue;
    }
    onSelect(option) {
        if (option.action) {
            option.action();
        } else {
            this.props.update([option.value, option.label]);
            this.state.isFloating = false;
        }
    }
}

Many2OneField.template = "web.Many2OneField";
Many2OneField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
    canOpen: { type: Boolean, optional: true },
    canCreate: { type: Boolean, optional: true },
    canWrite: { type: Boolean, optional: true },
    canQuickCreate: { type: Boolean, optional: true },
    canCreateEdit: { type: Boolean, optional: true },
    searchLimit: { type: Number, optional: true },
    relation: String,
};
Many2OneField.defaultProps = {
    canOpen: true,
    canCreate: true,
    canWrite: true,
    canQuickCreate: true,
    canCreateEdit: true,
    searchLimit: 7,
};
Many2OneField.components = {
    AutoComplete,
};
Many2OneField.displayName = _lt("Many2one");
Many2OneField.supportedTypes = ["many2one"];
Many2OneField.extractProps = (fieldName, record, attrs) => {
    const noOpen = Boolean(attrs.options.no_open);
    const noCreate = Boolean(attrs.options.no_create);
    const canCreate = attrs.can_create && Boolean(JSON.parse(attrs.can_create));
    const canWrite = attrs.can_write && Boolean(JSON.parse(attrs.can_write));
    const noQuickCreate = Boolean(attrs.options.no_quick_create);
    const noCreateEdit = Boolean(attrs.options.no_create_edit);

    return {
        placeholder: attrs.placeholder,
        canOpen: !noOpen,
        canCreate: canCreate && !noCreate,
        canWrite,
        canQuickCreate: canCreate && !noQuickCreate,
        canCreateEdit: canCreate && !noCreateEdit,
        relation: record.fields[fieldName].relation,
    };
};

registry.category("fields").add("many2one", Many2OneField);
