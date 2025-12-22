import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { formView } from "@web/views/form/form_view";
import { SettingsConfirmationDialog } from "./settings_confirmation_dialog";
import { SettingsFormRenderer } from "./settings_form_renderer";

import { useSubEnv, useState, useRef, useEffect } from "@odoo/owl";

export class SettingsFormController extends formView.Controller {
    static template = "web.SettingsFormView";
    static components = {
        ...formView.Controller.components,
        Renderer: SettingsFormRenderer,
    };

    setup() {
        super.setup();
        useAutofocus();
        this.state = useState({ displayNoContent: false });
        this.searchState = useState({ value: "" });
        this.rootRef = useRef("root");
        this.canCreate = false;
        useSubEnv({ searchState: this.searchState });
        useEffect(
            () => {
                if (this.searchState.value) {
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
                } else {
                    this.state.displayNoContent = false;
                }
            },
            () => [this.searchState.value]
        );
        useEffect(() => {
            if (this.env.__getLocalState__) {
                this.env.__getLocalState__.remove(this);
            }
        });

        this.initialApp = "module" in this.props.context ? this.props.context.module : "";
    }

    get modelParams() {
        const headerFields = Object.values(this.archInfo.fieldNodes)
            .filter((fieldNode) => fieldNode.options.isHeaderField)
            .map((fieldNode) => fieldNode.name);
        return {
            ...super.modelParams,
            headerFields,
            onChangeHeaderFields: () => this._confirmSave(),
        };
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "cancel") {
            return true;
        }
        if (
            (await this.model.root.isDirty()) &&
            !["execute"].includes(clickParams.name) &&
            !clickParams.noSaveDialog
        ) {
            return this._confirmSave();
        } else {
            return this.model.root.save();
        }
    }

    displayName() {
        return _t("Settings");
    }

    async beforeLeave() {
        const dirty = await this.model.root.isDirty();
        if (dirty) {
            return this._confirmSave();
        }
    }

    //This is needed to avoid the auto save when unload
    beforeUnload() {}

    //This is needed to avoid the auto save when visibility change
    beforeVisibilityChange() {}

    async save() {
        await this.env.onClickViewButton({
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
                body: _t("Would you like to save your changes?"),
                confirm: async () => {
                    await this.save();
                    // It doesn't make sense to do the action of the button
                    // as the res.config.settings `execute` method will trigger a reload.
                    _continue = false;
                    resolve();
                },
                cancel: async () => {
                    await this.model.root.discard();
                    await this.model.root.save();
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
