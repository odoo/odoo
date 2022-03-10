/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf, escape } from "@web/core/utils/strings";
import { standardFieldProps } from "./standard_field_props";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

const { Component, onWillStart, onWillUpdateProps, useState } = owl;

export class Many2OneField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");

        this.displayName = "";
        this.extraLines = [];

        this.state = useState({
            isFloating: !this.props.value,
        });

        onWillStart(async () => {
            [this.displayName, ...this.extraLines] = await this.loadDisplayName(this.props.value);
        });
        onWillUpdateProps(async (nextProps) => {
            this.state.isFloating = !nextProps.value;
            if (this.props.value !== nextProps.value) {
                [this.displayName, ...this.extraLines] = await this.loadDisplayName(
                    nextProps.value
                );
            }
        });
    }

    get searchLimit() {
        return this.constructor.searchLimit;
    }
    get hasExternalButton() {
        return !this.props.noOpen && !!this.props.value && !this.state.isFloating;
    }
    get canCreate() {
        return this.props.canCreate && !this.props.noCreate;
    }
    get canQuickCreate() {
        return this.canCreate && !this.props.noQuickCreate;
    }
    get canCreateEdit() {
        return this.canCreate && !this.props.noCreateEdit;
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

    getDomain() {
        return this.props.record
            .getFieldDomain(this.props.name)
            .toList(this.props.record.getFieldContext(this.props.name));
    }

    async loadDisplayName(value) {
        // FIXME WOWL should not be done here (in list, we do a name_get by line)
        if (this.props.alwaysReload && value) {
            const nameGet = await this.orm.call(this.props.relation, "name_get", [value[0]], {
                context: this.props.record.getFieldContext(this.props.name),
            });
            return nameGet[0][1].split("\n").map((line) => line.trim());
        }
        return [this.props.format(value)];
    }

    async loadRecordSource(request) {
        const records = await this.orm.call(this.props.relation, "name_search", [], {
            name: request,
            args: this.getDomain(),
            operator: "ilike",
            limit: this.searchLimit + 1,
            context: this.props.record.getFieldContext(this.props.name),
        });

        const options = records.map((result) => ({
            value: result[0],
            label: result[1],
        }));

        // Add "Search more..." option if records count is higher than the limit
        if (this.searchLimit < records.length) {
            options.push({
                label: this.env._t("Search More..."),
                classList: "o_m2o_dropdown_option",
                action: () => {
                    console.log("search more");
                },
            });
        }

        if (request.length) {
            // "Quick create" option
            if (this.canQuickCreate && !records.some((record) => record[1] === request)) {
                options.push({
                    label: sprintf(this.env._t(`Create "%s"`), escape(request)),
                    classList: "o_m2o_dropdown_option",
                    action: () => {
                        console.log("create");
                    },
                });
            }

            // "Create and Edit" option
            if (this.canCreateEdit) {
                options.push({
                    label: this.env._t(`Create and Edit...`),
                    classList: "o_m2o_dropdown_option",
                    action: () => {
                        console.log("create and edit");
                    },
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
        } else if (!this.props.value && (this.canQuickCreate || this.canCreateEdit)) {
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
            [[this.props.value[0]]],
            { context: this.props.record.getFieldContext(this.props.name) }
        );
        await this.action.doAction(action);
    }
    async openDialog(resId) {
        const viewId = await this.orm.call(
            this.props.relation,
            "get_formview_id",
            [[this.props.value[0]]],
            { context: this.props.record.getFieldContext(this.props.name) }
        );

        const record = this.env.model.createDataPoint("record", {
            activeFields: {},
            fields: {},
            resId,
            resModel: this.props.relation,
            context: this.props.record.getFieldContext(this.props.name),
            mode: this.props.readonly ? "readonly" : "edit",
            viewId,
        });
        this.dialog.add(FormViewDialog, {
            record,
            title: sprintf(
                this.env._t("Open: %s"),
                this.props.record.activeFields[this.props.name].string
            ),
        });
    }

    onClick() {
        this.openAction();
    }
    onExternalBtnClick() {
        this.openDialog(this.props.value[0]);
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
    noOpen: { type: Boolean, optional: true },
    noCreate: { type: Boolean, optional: true },
    canCreate: { type: Boolean, optional: true },
    canWrite: { type: Boolean, optional: true },
    noQuickCreate: { type: Boolean, optional: true },
    noCreateEdit: { type: Boolean, optional: true },
    alwaysReload: { type: Boolean, optional: true },
    relation: String,
};
Many2OneField.defaultProps = {
    canCreate: true,
    canWrite: true,
};
Many2OneField.components = {
    AutoComplete,
};
Many2OneField.displayName = _lt("Many2one");
Many2OneField.supportedTypes = ["many2one"];
Many2OneField.extractProps = (fieldName, record, attrs) => {
    return {
        noOpen: Boolean(attrs.options.no_open),
        noCreate: Boolean(attrs.options.no_create),
        canCreate: attrs.can_create && Boolean(JSON.parse(attrs.can_create)),
        canWrite: attrs.can_write && Boolean(JSON.parse(attrs.can_write)),
        noQuickCreate: Boolean(attrs.options.no_quick_create),
        noCreateEdit: Boolean(attrs.options.no_create_edit),
        alwaysReload: Boolean(attrs.options.always_reload),
        relation: record.fields[fieldName].relation,
    };
};
Many2OneField.searchLimit = 7;

registry.category("fields").add("many2one", Many2OneField);
