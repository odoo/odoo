import { COLLABORATION_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class HtmlField extends Component {
    static template = "html_editor.HtmlField";
    static props = {
        ...standardFieldProps,
        isCollaborative: { type: Boolean, optional: true },
    };
    static components = {
        Wysiwyg,
    };

    setup() {
        const { model } = this.props.record;
        useBus(model.bus, "WILL_SAVE_URGENTLY", () => this.commitChanges());
        useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
            detail.proms.push(this.commitChanges())
        );
        this.busService = this.env.services.bus_service;

        this.isDirty = false;
        this.state = useState({ key: 0 });
        this.lastValue = this.props.record.data[this.props.name].toString();
        useRecordObserver((record) => {
            // Reset Wysiwyg when we discard
            if (
                !this.isDirty &&
                !record.dirty &&
                this.lastValue !== record.data[this.props.name].toString()
            ) {
                this.state.key++;
            }
        });
    }

    get wysiwygKey() {
        return `${this.props.record.resId}_${this.state.key}`;
    }

    async updateValue() {
        this.lastValue = this.editor.getContent();
        await this.props.record.update({ [this.props.name]: this.lastValue });
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", false);
        this.isDirty = false;
    }

    async commitChanges() {
        if (this.isDirty) {
            await this.updateValue();
        }
    }

    async onBlur() {
        await this.updateValue();
    }

    onLoad(editor) {
        this.editor = editor;
    }

    onChange() {
        this.isDirty = true;
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", true);
    }

    getConfig() {
        const config = {
            content: this.props.record.data[this.props.name],
            Plugins: [
                ...MAIN_PLUGINS,
                ...(this.props.isCollaborative ? COLLABORATION_PLUGINS : []),
            ],
            classList: this.classList,
            onChange: this.onChange.bind(this),
            busService: this.busService,
            collaborationChannel: this.props.isCollaborative && {
                collaborationModelName: this.props.record.resModel,
                collaborationFieldName: this.props.name,
                collaborationResId: parseInt(this.props.record.resId),
            },
            peerId: this.generateId(),
        };
        return config;
    }
    generateId() {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2, 52)).toString();
    }
}

export const htmlField = {
    component: HtmlField,
    displayName: _t("Html"),
    supportedTypes: ["html"],
    extractProps({ attrs, options }, dynamicInfo) {
        return {
            isCollaborative: options.collaborative,
        };
    },
};

registry.category("fields").add("html", htmlField, { force: true });
