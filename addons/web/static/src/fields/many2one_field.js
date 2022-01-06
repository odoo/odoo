/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "./standard_field_props";
import { Domain } from "@web/core/domain";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

const { Component } = owl;
const { onWillStart, onWillUpdateProps, useState } = owl.hooks;

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
    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }
    get noOpen() {
        return this.props.options.no_open;
    }
    get hasExternalButton() {
        return !this.noOpen && !!this.props.value && !this.state.isFloating;
    }
    get canCreate() {
        const attr =
            "canCreate" in this.props.attrs ? JSON.parse(this.props.attrs.canCreate) : true;
        const option = !this.props.options.no_create;
        return attr && option;
    }
    get canWrite() {
        return "canWrite" in this.props.attrs ? JSON.parse(this.props.attrs.canWrite) : true;
    }
    get canQuickCreate() {
        return this.canCreate && !this.props.options.no_quick_create;
    }
    get canCreateEdit() {
        return this.canCreate && !this.props.options.no_create_edit;
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
        return new Domain(this.props.attrs.domain).toList(
            this.props.record.getFieldContext(this.props.name)
        );
    }

    async loadDisplayName(value) {
        if (this.props.options.always_reload && value) {
            const nameGet = await this.orm.call(this.relation, "name_get", [value[0]], {
                context: this.props.record.getFieldContext(this.props.name),
            });
            return nameGet[0][1].split("\n").map((line) => line.trim());
        }
        return [this.props.formatValue(value)];
    }

    async loadRecordSource(request) {
        const records = await this.orm.call(this.relation, "name_search", [], {
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
                    label: sprintf(this.env._t(`Create "%s"`), owl.utils.escape(request)),
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
            this.props.record.fields[this.props.name].relation,
            "get_formview_action",
            [[this.props.value[0]]],
            { context: this.props.record.getFieldContext(this.props.name) }
        );
        await this.action.doAction(action);
    }
    async openDialog(resId) {
        const viewId = await this.orm.call(
            this.props.record.fields[this.props.name].relation,
            "get_formview_id",
            [[this.props.value[0]]],
            { context: this.props.record.getFieldContext(this.props.name) }
        );

        const record = this.env.model.createDataPoint("record", {
            activeFields: {},
            fields: {},
            resId,
            resModel: this.relation,
            context: this.props.record.getFieldContext(this.props.name),
            viewId,
        });
        this.dialog.add(FormViewDialog, {
            record,
            readonly: this.props.readonly,
            title: this.props.record.activeFields[this.props.name].string,
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
Object.assign(Many2OneField, {
    template: "web.Many2OneField",
    props: {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    },
    components: {
        AutoComplete,
    },

    displayName: _lt("Many2one"),
    supportedTypes: ["many2one"],

    searchLimit: 7,
});

registry.category("fields").add("many2one", Many2OneField);
