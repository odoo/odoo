/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useAutofocus } from "@web/core/utils/hooks";
import { FormView } from "@web/views/form/form_view";
import { useViewButtons } from "@web/views/view_button/hook";
import { Field } from "../../fields/field";
import { SettingsConfirmationDialog } from "./settings_confirmation_dialog";
import { SettingsFormRender } from "./settings_form_render";

const { useSubEnv, useState, useRef, useEffect } = owl;

const fieldRegistry = registry.category("fields");

class SettingsFormView extends FormView {
    setup() {
        const parseFieldNode = Field.parseFieldNode;
        Field.parseFieldNode = function (node) {
            const widgetName = node.getAttribute("widget");
            const name = `base_settings.${widgetName}`;
            let widget = null;
            if (fieldRegistry.contains(name)) {
                widget = fieldRegistry.get(name);
            }
            const fieldInfo = parseFieldNode.call(this, ...arguments);
            if (widget) {
                fieldInfo.FieldComponent = widget;
            }
            return fieldInfo;
        };
        super.setup();
        Field.parseFieldNode = parseFieldNode;
        const beforeExecuteAction = async (clickParams) => {
            let _continue = true;
            if (this.model.root.isDirty && !["cancel", "execute"].includes(clickParams.name)) {
                const message = this.env._t("Would you like to save your changes?");
                await new Promise((resolve) => {
                    this.dialogService.add(
                        SettingsConfirmationDialog,
                        {
                            body: message,
                            confirm: async () => {
                                await this.save();
                            },
                            cancel: () => {},
                            stayHere: () => {
                                _continue = false;
                            },
                        },
                        { onClose: resolve }
                    );
                });
            }
            return _continue;
        };
        useViewButtons(this.model, useRef("root"), { beforeExecuteAction });
        useAutofocus();
        this.state = useState({ displayNoContent: false });
        this.searchInput = useState({ value: "" });
        this.rootRef = useRef("root");
        useSubEnv({ searchValue: this.searchInput });
        useSubEnv({
            config: {
                ...this.env.config,
                breadcrumbs: [
                    {
                        jsId: "js_id_settings",
                        name: "Settings",
                    },
                ],
            },
        });
        useEffect(
            () => {
                if (this.rootRef.el.querySelector(".settings .o_setting_box")) {
                    this.state.displayNoContent = false;
                } else {
                    this.state.displayNoContent = true;
                }
            },
            () => [this.searchInput.value]
        );
        useEffect(() => {
            if (this.env.__beforeLeave__) {
                this.env.__beforeLeave__.remove(this);
            }
            if (this.env.__getLocalState__) {
                this.env.__getLocalState__.remove(this);
            }
        });
    }

    onSearchInput(ev) {
        this.searchInput.value = ev.target.value;
    }

    async save() {
        this.env.onClickViewButton({
            clickParams: {
                name: "execute",
                type: "object",
            },
            record: this.model.root,
        });
    }

    discard() {
        this.env.onClickViewButton({
            clickParams: {
                name: "cancel",
                type: "object",
                special: "cancel",
            },
            record: this.model.root,
        });
    }
}

SettingsFormView.components = { ...FormView.components, Renderer: SettingsFormRender };
SettingsFormView.display = {};
SettingsFormView.template = "web.SettingsFormView";
SettingsFormView.buttonTemplate = "web.SettingsFormView.Buttons";

registry.category("views").add("base_settings", SettingsFormView);
