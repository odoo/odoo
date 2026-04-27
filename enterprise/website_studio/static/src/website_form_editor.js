import options from "@web_editor/js/editor/snippets.options";
import { _t } from "@web/core/l10n/translation";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { sprintf } from "@web/core/utils/strings";

const IR_MODEL_SPEC = {
    model: {},
    name: {},
    website_form_label: {},
    website_form_key: {},
    website_form_access: {},
};

options.registry.WebsiteFormEditor.include({
    async _fetchModels() {
        const models = await this._super();
        models.forEach((m) => {
            m.website_form_access = true;
        });
        const currentModel = this.$target[0].dataset.model_name;
        if (currentModel && !models.find((m) => m.model === currentModel)) {
            const res = await this.orm.webSearchRead("ir.model", [["model", "=", currentModel]], {
                specification: IR_MODEL_SPEC,
            });
            for (const model of res.records) {
                if (!model.website_form_label) {
                    model._isVirtual = true;
                    model.website_form_label = this._getNewFormLabel(model);
                }
                models.push(model);
            }
        }
        return models;
    },

    _isFormAccessEditable(model) {
        return (
            model &&
            (model.website_form_key === false ||
                model.website_form_key.startsWith("website_studio."))
        );
    },

    _getNewFormLabel(model) {
        return sprintf(_t("Create %s"), model.name);
    },

    _makeSelectAction() {
        const selectActionEl = this._super(...arguments);
        if (!selectActionEl) {
            return;
        }
        const anyModelAction = document.createElement("we-button");
        anyModelAction.textContent = _t("More models");
        anyModelAction.dataset.selectAction = "website_studio.form_more_model";
        selectActionEl.append(anyModelAction);
        return selectActionEl;
    },

    _computeWidgetVisibility(widgetName) {
        if (widgetName === "enable_website_form_access") {
            return this._isFormAccessEditable(this.activeForm);
        }
        return this._super(...arguments);
    },

    setFormAccess(preview, widgetValue) {
        if (!preview) {
            this._setFormAccess(this.activeForm, widgetValue === "true");
            return this._saveFormAccess(this.activeForm);
        }
    },

    async _setFormAccess(model, newValue) {
        if (!model) {
            return;
        }
        if (this._isFormAccessEditable(model)) {
            const toWrite = { website_form_access: newValue };
            if (!("_old_website_form_access" in model)) {
                model._old_website_form_access = model.website_form_access;
            }
            if (newValue && model._isVirtual) {
                toWrite.website_form_label = model.website_form_label;
                toWrite.website_form_key = `website_studio.${model.model}`;
            }
            Object.assign(model, toWrite);
        }
    },

    cleanForSave() {
        return Promise.all([this._super(...arguments), this._saveFormAccess(this.activeForm)]);
    },

    async _saveFormAccess(model) {
        if (
            model &&
            "_old_website_form_access" in model &&
            model._old_website_form_access !== model.website_form_access
        ) {
            const { website_form_access, website_form_key, website_form_label } = model;
            const toWrite = {
                website_form_access,
            };
            if (model._isVirtual) {
                Object.assign(toWrite, {
                    website_form_key,
                    website_form_label,
                });
            }
            const res = await this.orm.webSave("ir.model", [model.id], toWrite, {
                specification: IR_MODEL_SPEC,
            });
            Object.assign(model, res[0]);
            delete model._old_website_form_access;
        }
    },

    _computeWidgetState(methodName, params) {
        if (methodName === "setFormAccess") {
            return this.activeForm?.website_form_access ? "true" : "";
        }
        return this._super(...arguments);
    },

    _selectModel() {
        return new Promise((resolve) => {
            this.dialog.add(
                SelectCreateDialog,
                {
                    title: _t("Select model"),
                    noCreate: true,
                    multiSelect: false,
                    resModel: "ir.model",
                    context: {
                        "list_view_ref": "website_studio.select_simple_ir_model",
                    },
                    domain: ["&", ["abstract", "=", false], ["transient", "=", false]],
                    onSelected: (resIds) => resolve(resIds[0]),
                },
                {
                    onClose: () => resolve(false),
                }
            );
        });
    },

    async selectAction(previewMode, value, params) {
        if (this.modelCantChange) {
            return;
        }
        if (value === "website_studio.form_more_model" && !previewMode) {
            const modelId = await this._selectModel();
            if (modelId) {
                if (!this.models.find((m) => m.id === modelId)) {
                    const model = (
                        await this.orm.webRead("ir.model", [modelId], {
                            specification: IR_MODEL_SPEC,
                        })
                    )[0];
                    if (!model.website_form_label) {
                        model._isVirtual = true;
                        model.website_form_label = this._getNewFormLabel(model);
                        // Force the retrieved model to be accessible publicly
                        // it will be saved on cleanForSave if the value changed and if it is still the activeForm
                        this._setFormAccess(model, true);
                    }
                    this.models.push(model);
                    this._makeSelectAction();
                }
                const proms = [this._applyFormModel(modelId)];
                // The synchronous part of this one should be triggered
                // after the synchronous part of applyFormModel
                proms.push(this._rerenderXML());
                return Promise.all(proms);
            }
            return;
        }
        return this._super(...arguments);
    },
});
