/** @odoo-module **/

import { useAutofocus } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { formView } from "@web/views/form/form_view";
import { SettingsConfirmationDialog } from "./settings_confirmation_dialog";
import { SettingsFormRenderer } from "./settings_form_renderer";

import { useSubEnv, useState, useRef, useEffect } from "@odoo/owl";

export class SettingsFormController extends formView.Controller {
    setup() {
        super.setup();
        useAutofocus();
        this.state = useState({ displayNoContent: false });
        this.searchState = useState({ value: "" });
        this.rootRef = useRef("root");
        useSubEnv({ searchState: this.searchState });
        useEffect(
            () => {
                if (
                    this.rootRef.el.querySelector(".o_settings_container:not(.d-none)") ||
                    this.rootRef.el.querySelector(
                        ".settings .o_settings_container:not(.d-none) .o_setting_box.o_searchable_setting"
                    )
                ) {
                    this.state.displayNoContent = false;
                } else {
                    this.state.displayNoContent = true;
                }
            },
            () => [this.searchState.value]
        );
        useEffect(() => {
            if (this.env.__getLocalState__) {
                this.env.__getLocalState__.remove(this);
            }
        });

        this.initialApp = "module" in this.props.context && this.props.context.module;
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "cancel") {
            return true;
        }
        if (
            this.model.root.isDirty &&
            !["execute"].includes(clickParams.name) &&
            !clickParams.noSaveDialog
        ) {
            return this._confirmSave();
        } else {
            return this.model.root.save({ stayInEdition: true });
        }
    }

    displayName() {
        return this.env._t("Settings");
    }

    beforeLeave() {
        if (this.model.root.isDirty) {
            return this._confirmSave();
        }
    }

    //This is needed to avoid the auto save when unload
    beforeUnload() {}

    //This is needed to avoid writing the id on the url
    updateURL() {}

    async saveButtonClicked() {
        await this._save();
    }

    async _save() {
        this.env.onClickViewButton({
            clickParams: {
                name: "execute",
                type: "object",
            },
            getResParams: () =>
                pick(this.model.root, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    }

    discard() {
        this.env.onClickViewButton({
            clickParams: {
                name: "cancel",
                type: "object",
                special: "cancel",
            },
            getResParams: () =>
                pick(this.model.root, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    }

    async _confirmSave() {
        let _continue = true;
        await new Promise((resolve) => {
            this.dialogService.add(SettingsConfirmationDialog, {
                body: this.env._t("Would you like to save your changes?"),
                confirm: async () => {
                    await this._save();
                    // It doesn't make sense to do the action of the button
                    // as the res.config.settings `execute` method will trigger a reload.
                    _continue = false;
                    resolve();
                },
                cancel: async () => {
                    await this.model.root.discard();
                    await this.model.root.save({ stayInEdition: true });
                    _continue = true;
                    resolve();
                },
                stayHere: () => {
                    _continue = false;
                    resolve();
                },
            });
        });
        return _continue;
    }
}

SettingsFormController.components = {
    ...formView.Controller.components,
    Renderer: SettingsFormRenderer,
};
SettingsFormController.template = "web.SettingsFormView";
