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
const { onWillStart, onWillUpdateProps } = owl.hooks;

export class Many2OneField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");

        this.displayName = "";
        this.extraLines = [];

        onWillStart(async () => {
            [this.displayName, ...this.extraLines] = await this.loadDisplayName(this.props.value);
        });
        onWillUpdateProps(async (nextProps) => {
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
        return !this.noOpen && !this.isFloating && !!this.props.value;
    }
    get isFloating() {
        return false;
        // return !!this.inputRef.el && this.displayName !== this.inputRef.el.value;
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
    async fetchAutoCompleteSources(request) {
        const trimmedRequest = request.trim();
        const suggestions = [];
        const context = Object.create(this);
        for (const source of registry.category("m2oAutoCompleteSources").getAll()) {
            await source(trimmedRequest, suggestions, context);
        }
        return suggestions;
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
    onChange(value) {
        if (!value) {
            this.props.update(false);
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

// FIXME: sources shouldn't be managed outside of many2one

async function searchRecords(request, suggestions, ctx) {
    const results = await ctx.orm.call(ctx.relation, "name_search", [], {
        name: request,
        args: ctx.getDomain(),
        operator: "ilike",
        limit: ctx.searchLimit + 1,
        context: ctx.props.record.getFieldContext(ctx.props.name),
    });

    suggestions.push(
        ...results.map((result) => {
            const displayName = ctx.props.formatValue(result);
            return {
                label: owl.utils.escape(displayName),
                onSelected: ({ setValue }) => {
                    setValue(displayName);
                    ctx.props.update(result);
                },
            };
        })
    );

    // Add "Search more..." option if results count is higher than the limit
    if (ctx.searchLimit < results.length) {
        suggestions.push({
            label: ctx.env._t("Search More..."),
            classList: "o_m2o_dropdown_option",
        });
    }
}

registry.category("m2oAutoCompleteSources").add("searchRecords", searchRecords);

function additionalOptions(request, suggestions, ctx) {
    if (request.length) {
        // "Quick create" option
        if (
            ctx.canQuickCreate &&
            !suggestions.some((s) => s.classList !== "o_m2o_dropdown_option" && s.label === request)
        ) {
            suggestions.push({
                label: sprintf(ctx.env._t(`Create "%s"`), owl.utils.escape(request)),
                classList: "o_m2o_dropdown_option",
            });
        }

        // "Create and Edit" option
        if (ctx.canCreateEdit) {
            suggestions.push({
                label: ctx.env._t(`Create and Edit...`),
                classList: "o_m2o_dropdown_option",
            });
        }

        // "No results" option
        if (!suggestions.length) {
            suggestions.push({
                label: ctx.env._t("No records"),
                classList: "o_m2o_no_result",
            });
        }
    } else if (!ctx.props.value && (ctx.canQuickCreate || ctx.canCreateEdit)) {
        // "Start typing" option
        suggestions.push({
            label: ctx.env._t("Start typing..."),
            classList: "o_m2o_start_typing",
        });
    }
}

registry.category("m2oAutoCompleteSources").add("additionalOptions", additionalOptions);
