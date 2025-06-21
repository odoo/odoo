import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";
import { SettingsConfirmationDialog } from "@web/webclient/settings_form_view/settings_confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { pick } from "@web/core/utils/objects";

patch(ViewButton.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
    },

    async onClick(ev) {
        const proceed = await this._confirmSave();

        if (!proceed) {
            return;
        }

        if (this.props.tag === "a") {
            ev.preventDefault();
        }

        if (this.props.onClick) {
            return this.props.onClick();
        }
    },

    discard() {
        const model = this.props.record || this.props.model;

        if (!model) {
            console.warn("No model available to discard or save.");
            return;
        }

        this.env.onClickViewButton({
            clickParams: {
                name: "cancel",
                type: "object",
                special: "cancel",
            },
            getResParams: () =>
                pick(model, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    },

    async _confirmSave() {
        let _continue = true;

        await new Promise((resolve) => {
            this.dialogService.add(SettingsConfirmationDialog, {
                body: _t("Would you like to save your changes?"),
                confirm: async () => {
                    // Check if `clickParams` is available
                    const clickParams = this.clickParams || {
                        name: "execute",
                        type: "object",
                    };

                    const model = this.props.record || this.props.model;
                    if (model) {
                        await this.env.onClickViewButton({
                            clickParams,
                            getResParams: () =>
                                pick(
                                    model,
                                    "context",
                                    "evalContext",
                                    "resModel",
                                    "resId",
                                    "resIds"
                                ),
                        });
                    } else {
                        console.warn("No model available to execute save.");
                    }

                    _continue = true;
                    resolve();
                },
                cancel: async () => {
                    const model = this.props.record || this.props.model;
                    if (model) {
                        await model?.discard?.();
                        await model?.save?.();
                    } else {
                        console.warn("No model available to discard or save.");
                    }
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
    },
});
