// @ts-check

/** @module @web/fields/specialized/ace/ace_field - Code editor field using the Ace/CodeEditor component */

import { Component, useState } from "@odoo/owl";
import { CodeEditor } from "@web/components/code_editor/code_editor";
import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { formatText } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useRecordObserver } from "@web/model/relational_model/record_hooks";

export class AceField extends Component {
    static template = "web.AceField";
    static props = {
        ...standardFieldProps,
        mode: { type: String, optional: true },
    };
    static defaultProps = {
        mode: "qweb",
    };
    static components = { CodeEditor };

    setup() {
        this.state = useState({});
        useRecordObserver((record) => {
            /** @type {any} */ (this.state).initialValue = formatText(
                record.data[this.props.name],
            );
        });

        this.isDirty = false;

        const { model } = this.props.record;
        useBus(
            model.bus,
            "WILL_SAVE_URGENTLY",
            /** @type {any} */ (() => this.commitChanges()),
        );
        useBus(
            model.bus,
            "NEED_LOCAL_CHANGES",
            /** @type {any} */ (
                ({ detail }) => detail.proms.push(this.commitChanges())
            ),
        );
    }

    get mode() {
        return this.props.mode === "xml" ? "qweb" : this.props.mode;
    }
    get theme() {
        return cookie.get("color_scheme") === "dark" ? "monokai" : "";
    }

    handleChange(editedValue) {
        if (/** @type {any} */ (this.state).initialValue !== editedValue) {
            this.isDirty = true;
        } else {
            this.isDirty = false;
        }
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", this.isDirty);
        this.editedValue = editedValue;
    }

    async commitChanges() {
        if (!this.props.readonly && this.isDirty) {
            if (/** @type {any} */ (this.state).initialValue !== this.editedValue) {
                await this.props.record.update({
                    [this.props.name]: this.editedValue,
                });
            }
            this.isDirty = false;
            this.props.record.model.bus.trigger("FIELD_IS_DIRTY", false);
        }
    }
}

export const aceField = {
    component: AceField,
    displayName: _t("Ace Editor"),
    supportedOptions: [
        {
            label: _t("Mode"),
            name: "mode",
            type: "string",
        },
    ],
    supportedTypes: ["text", "html"],
    extractProps: ({ options }) => ({
        mode: options.mode,
    }),
};

registry.category("fields").add("ace", aceField);
registry.category("fields").add("code", aceField);
