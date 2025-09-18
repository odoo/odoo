// @ts-check

/** @module @web/views/settings/settings_form_view - View descriptor for the settings form view (base_setup) with custom record, model, and compiler */

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { intersection } from "@web/core/utils/collections/arrays";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formView } from "@web/views/form/form_view";

import { SettingsFormCompiler } from "./settings_form_compiler";
import { SettingsFormController } from "./settings_form_controller";
import { SettingsFormRenderer } from "./settings_form_renderer";

/** Record subclass that handles header-field changes with confirmation dialogs. */
class SettingRecord extends formView.Model.Record {
    _update(changes) {
        const changedFields = Object.keys(changes);
        let dirty = true;
        if (
            intersection(changedFields, /** @type {any} */ (this.model)._headerFields)
                .length === changedFields.length
        ) {
            dirty = this.dirty;
            if (this.dirty) {
                /** @type {any} */ (this.model)
                    ._onChangeHeaderFields()
                    .then(async (isDiscard) => {
                        if (isDiscard) {
                            await /** @type {any} */ (super._update)(changes);
                            this.dirty = false;
                        } else {
                            // We need to apply and then undo the changes
                            // to force the field component to be render
                            // and restore the previous value (like RadioField))
                            const undoChanges = this._applyChanges(changes);
                            undoChanges();
                        }
                    });
                return;
            }
        }
        const prom = /** @type {any} */ (super._update)(changes);
        this.dirty = dirty;
        return prom;
    }
}

/** Model subclass that tracks header fields and forces resId=false on config reload. */
class SettingModel extends formView.Model {
    static withCache = false;

    setup(params) {
        super.setup(/** @type {any} */ (params));
        this._headerFields = params.headerFields;
        this._onChangeHeaderFields = params.onChangeHeaderFields;
    }
    _getNextConfig(currentConfig, params) {
        const nextConfig = super._getNextConfig(currentConfig, params);
        nextConfig.resId = false;
        return nextConfig;
    }
}
SettingModel.Record = SettingRecord;

export const settingsFormView = {
    ...formView,
    display: {},
    Model: SettingModel,
    ControlPanel: ControlPanel,
    Controller: SettingsFormController,
    Compiler: SettingsFormCompiler,
    Renderer: SettingsFormRenderer,
    props: (genericProps, view) => {
        [...genericProps.arch.querySelectorAll("setting[type='header'] field")].forEach(
            (el) => {
                const options = evaluateExpr(el.getAttribute("options") || "{}");
                options.isHeaderField = true;
                el.setAttribute("options", JSON.stringify(options));
            },
        );
        return formView.props(genericProps, view);
    },
};

registry.category("views").add("base_settings", settingsFormView);
