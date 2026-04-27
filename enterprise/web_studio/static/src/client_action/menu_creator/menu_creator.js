import { Component, useState } from "@odoo/owl";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

import { _t } from "@web/core/l10n/translation";

import { useDialogConfirmation } from "@web_studio/client_action/utils";
import { ModelConfiguratorDialog } from "../model_configurator/model_configurator";
import { RecordSelector } from "@web/core/record_selectors/record_selector";

export class MenuCreatorModel {
    constructor({ allowNoModel } = {}) {
        this.data = {
            modelId: false,
            menuName: "",
            modelChoice: "new",
        };

        // Info to select what kind of model is linked to the menu
        this.modelChoiceSelection = {
            new: _t("New Model"),
            existing: _t("Existing Model"),
        };

        if (allowNoModel) {
            this.modelChoiceSelection.parent = _t("Parent Menu");
        }
    }

    validateField(fieldName) {
        if (fieldName === "menuName") {
            return !!this.data.menuName;
        } else if (fieldName === "modelId") {
            return this.data.modelChoice === "existing" ? !!this.data.modelId : true;
        }
    }

    get isValid() {
        return ["menuName", "modelId"].every((fName) => this.validateField(fName));
    }
}

export class MenuCreator extends Component {
    static template = "web_studio.MenuCreator";
    static components = { RecordSelector };
    static props = {
        menuCreatorModel: { type: Object },
        showValidation: { type: Boolean, optional: true },
    };
    static defaultProps = {
        showValidation: false,
    };

    get multiRecordSelectorProps() {
        return {
            resModel: "ir.model",
            resId: this.state.data.modelId && this.state.data.modelId[0],
            update: (resId) => (this.state.data.modelId = [resId]),
            domain: [
                ["transient", "=", false],
                ["abstract", "=", false],
            ],
        };
    }

    setup() {
        this.state = useState(this.props.menuCreatorModel);
    }

    isValid(fieldName) {
        return this.props.showValidation ? this.state.validateField(fieldName) : true;
    }
}

export class MenuCreatorDialog extends Component {
    static template = "web_studio.MenuCreatorDialog";
    static components = { Dialog, MenuCreator };
    static props = { confirm: { type: Function }, close: { type: Function } };

    setup() {
        this.addDialog = useOwnedDialogs();
        this.menuCreatorModel = useState(new MenuCreatorModel({ allowNoModel: true }));
        this.state = useState({ showValidation: false });
        const { confirm, cancel } = useDialogConfirmation({
            confirm: async (data = {}) => {
                if (!this.menuCreatorModel.isValid) {
                    this.state.showValidation = true;
                    return false;
                }
                await this.props.confirm(data);
            },
        });
        this._confirm = confirm;
        this._cancel = cancel;
    }

    confirm(data = {}) {
        this._confirm({ ...this.menuCreatorModel.data, ...data });
    }

    onCreateNewModel() {
        if (!this.menuCreatorModel.isValid) {
            this.state.showValidation = true;
            return;
        }
        this.addDialog(ModelConfiguratorDialog, {
            confirmLabel: _t("Create Menu"),
            confirm: (data) => {
                this.confirm({ modelOptions: data });
            },
        });
    }
}
