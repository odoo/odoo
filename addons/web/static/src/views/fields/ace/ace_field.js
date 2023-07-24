/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "../standard_field_props";

import { CodeEditor } from "@web/core/code_editor/code_editor";
import { Component, useState } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { useDebounced } from "@web/core/utils/timing";

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
        this.cookies = useService("cookie");
        this.debouncedCommit = useDebounced(this.commitChanges, 5000);

        this.state = useState({});
        useRecordObserver((record) => {
            this.state.value = record.data[this.props.name];
        });

        const { model } = this.props.record;
        useBus(model.bus, "WILL_SAVE_URGENTLY", () => this.commitChanges());
        useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
            detail.proms.push(this.commitChanges())
        );
    }

    get mode() {
        return this.props.mode === "xml" ? "qweb" : this.props.mode;
    }
    get theme() {
        return this.cookies.current.color_scheme === "dark" ? "monokai" : "";
    }

    handleChange(newValue) {
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", true);
        this.state.value = newValue;
        this.debouncedCommit();
    }

    async commitChanges() {
        if (!this.props.readonly) {
            const value = this.state.value;
            if (this.props.record.data[this.props.name] !== value) {
                await this.props.record.update({ [this.props.name]: value });
            }
        }
    }
}

export const aceField = {
    component: AceField,
    displayName: _lt("Ace Editor"),
    supportedOptions: [
        {
            label: _lt("Mode"),
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
