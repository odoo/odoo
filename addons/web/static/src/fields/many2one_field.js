/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useEffect, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
const { onWillStart, onWillUpdateProps, useRef, useState } = owl.hooks;

export class Many2OneField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.inputRef = useRef("input");

        this.extraLines = [];

        useEffect(() => {
            if (this.inputRef.el) {
                this.autoComplete(this.autoCompleteOptions);
            }
            return () => {
                if (this.inputRef.el) {
                    this.autoComplete("destroy");
                }
            };
        });

        onWillStart(async () => {
            this.extraLines = await this.loadExtraLines(this.props.value);
        });
        onWillUpdateProps(async (nextProps) => {
            if (this.props.value !== nextProps.value) {
                this.extraLines = await this.loadExtraLines(nextProps.value);
            }
        });
    }

    get autoCompleteOptions() {
        return {
            autoFocus: true,
            html: true,
            minLength: 0,
            delay: this.constructor.AUTOCOMPLETE_DELAY,
            classes: {
                "ui-autocomplete": "dropdown-menu",
            },
            position: { my: "left top", at: "left bottom" },
            create() {
                $(this).data("ui-autocomplete")._renderMenu = function (ulWrapper, entries) {
                    for (const entry of entries) {
                        this._renderItemData(ulWrapper, entry);
                    }
                    ulWrapper.find("li > a").addClass("dropdown-item");
                };
            },
            source: this.onAutoCompleteSource.bind(this),
            select: this.onAutoCompleteSelect.bind(this),
            focus: this.onAutoCompleteFocus.bind(this),
            open: this.onAutoCompleteOpen.bind(this),
            close: this.onAutoCompleteClose.bind(this),
        };
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
    get displayName() {
        return this.props.value ? this.getDisplayName(this.props.value[1]) : "";
    }
    get isFloating() {
        return !!this.inputRef.el && this.displayName !== this.inputRef.el.value;
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

    getDisplayName(value) {
        return value.split("\n")[0].trim();
    }

    autoComplete(...args) {
        return $(this.inputRef.el).autocomplete(...args);
    }

    async loadExtraLines(value) {
        if (this.props.options.always_reload && value) {
            const nameGet = await this.orm.call(this.relation, "name_get", [value[0]]);
            return nameGet[0][1].split("\n").slice(1);
        }
        return [];
    }
    async fetchAutoCompleteSources(term) {
        const trimmedTerm = term.trim();
        const results = await this.search(trimmedTerm);

        if (trimmedTerm.length) {
            // "Quick create" option
            const nameExists = results.some((result) => result.value === trimmedTerm);
            if (this.canQuickCreate && !nameExists) {
                results.push({
                    label: sprintf(
                        this.env._t(`Create "<strong>%s</strong>"`),
                        owl.utils.escape(trimmedTerm)
                    ),
                    classname: "o_m2o_dropdown_option",
                });
            }

            // "Create and Edit" option
            if (this.canCreateEdit) {
                results.push({
                    label: this.env._t("Create and Edit..."),
                    classname: "o_m2o_dropdown_option",
                });
            }

            // "No results" option
            if (!results.length) {
                results.push({
                    label: this.env._t("No records"),
                    classname: "o_m2o_no_result",
                });
            }
        } else if (!this.props.value && (this.canQuickCreate || this.canCreateEdit)) {
            // "Start typing" option
            results.push({
                label: this.env._t("Start typing..."),
                classname: "o_m2o_start_typing",
            });
        }

        return results;
    }

    async search(term = "") {
        const results = await this.orm.call(
            this.props.record.fields[this.props.name].relation,
            "name_search",
            [],
            {
                name: term.trim(),
                args: [],
                operator: "ilike",
                limit: 8,
            }
        );

        return results.map(([id, fullName]) => {
            const displayName = this.getDisplayName(fullName);
            return {
                label: owl.utils.escape(displayName),
                value: displayName,
                onSelected: () => {
                    this.inputRef.el.value = displayName;
                    this.props.update([id, fullName]);
                },
            };
        });
    }

    async openAction() {
        const action = await this.orm.call(
            this.props.record.fields[this.props.name].relation,
            "get_formview_action",
            [[this.props.value[0]]],
            {
                /* context: this.props.record.context */
            }
        );
        await this.action.doAction(action);
    }
    async openDialog() {
        // FIXME: should open a form dialog
        const action = await this.orm.call(
            this.props.record.fields[this.props.name].relation,
            "get_formview_action",
            [[this.props.value[0]]],
            {
                /* context: this.props.record.context */
            }
        );
        await this.action.doAction(action);
    }

    onAutoCompleteFocus() {}
    onAutoCompleteOpen() {}
    onAutoCompleteClose() {}
    onAutoCompleteSelect(e, { item }) {
        if (e.key === "Enter") {
            // on Enter we do not want any additional effect, such as
            // navigating to another field
            e.stopImmediatePropagation();
            e.preventDefault();
        }
        if (item.onSelected) {
            item.onSelected();
        }
        return false;
    }
    async onAutoCompleteSource(request, response) {
        const term = request.term.trim();
        const results = await this.fetchAutoCompleteSources(term);
        response(results);
    }

    onChange(ev) {
        if (!ev.target.value) {
            this.props.update(false);
        }
    }
    onClick() {
        this.openAction();
    }
    onExternalBtnClick() {
        this.openDialog();
    }
    onInputClick() {
        if (this.autoComplete("widget").is(":visible")) {
            this.autoComplete("close");
        } else if (this.isFloating) {
            this.autoComplete("search"); // search with the input's content
        } else {
            this.autoComplete("search", ""); // search with the empty string
        }
    }
}

Object.assign(Many2OneField, {
    template: "web.Many2OneField",
    props: {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    },

    displayName: _lt("Many2one"),
    supportedTypes: ["many2one"],

    AUTOCOMPLETE_DELAY: 200,
});

registry.category("fields").add("many2one", Many2OneField);

export async function preloadMany2one(orm, record, fieldName) {
    if (record.activeFields[fieldName].options.always_reload && record.data[fieldName]) {
        const nameGet = await orm.call(record.fields[fieldName].relation, "name_get", [
            record.data[fieldName][0],
        ]);
        return nameGet[0][1].split("\n").slice(1);
    }
    return [];
}

registry.category("preloadedData").add("many2one", preloadMany2one);
