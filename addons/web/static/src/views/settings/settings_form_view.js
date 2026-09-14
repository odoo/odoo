// @ts-check
/** @odoo-module native */

import { reportUncaught } from "@web/core/errors/error_utils";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { intersection } from "@web/core/utils/collections/arrays";
import { deepCopy } from "@web/core/utils/collections/objects";
import { parseXML } from "@web/core/utils/dom/xml";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formView } from "@web/views/form/form_view";
import { elementToIR } from "@web/views/ir/view_ir";
import { visitIR } from "@web/views/view_arch_parser";

import { SettingsFormCompiler } from "./settings_form_compiler.js";
import { SettingsFormController } from "./settings_form_controller.js";
import { SettingsFormRenderer } from "./settings_form_renderer.js";

class SettingRecord extends formView.Model.Record {
    updateLocked(changes) {
        const changedFields = Object.keys(changes);
        let dirty = true;
        if (
            intersection(changedFields, /** @type {any} */ (this.model)._headerFields)
                .length === changedFields.length
        ) {
            dirty = this.dirty;
            if (this.dirty) {
                /** @type {any} */ (
                    async () => {
                        const isDiscard = await /** @type {any} */ (
                            this.model
                        )._onChangeHeaderFields();
                        if (isDiscard) {
                            await /** @type {any} */ (super.updateLocked)(changes);
                            this.dirty = false;
                        } else {
                            const undoChanges = this.applyChanges(
                                changes,
                                {},
                                {
                                    undoable: true,
                                },
                            );
                            undoChanges();
                        }
                    }
                )().catch(reportUncaught);
                return;
            }
        }
        const prom = /** @type {any} */ (super.updateLocked)(changes);
        this.dirty = dirty;
        return prom;
    }
}

class SettingModel extends formView.Model {
    static withCache = false;

    setup(params, services) {
        super.setup(/** @type {any} */ (params), services);
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

const settingsFormView = {
    ...formView,
    display: {},
    Model: SettingModel,
    ControlPanel: ControlPanel,
    Controller: SettingsFormController,
    Compiler: SettingsFormCompiler,
    Renderer: SettingsFormRenderer,
    // a field under <setting type="header"> is marked in its options before
    // the form parser reads the tree; the mark goes on a copy of the IR, the
    // one handed in may be the view cache's
    props: (genericProps, view) => {
        const { arch, ir } = genericProps;
        const marked = deepCopy(
            ir ?? elementToIR(typeof arch === "string" ? parseXML(arch) : arch),
        );
        visitIR(marked, (node) => {
            if (node.kind !== "setting" || node.attrs?.type !== "header") {
                return;
            }
            visitIR(node, (child) => {
                if (child.kind === "field") {
                    const attrs = (child.attrs ??= {});
                    const options = evaluateExpr(attrs.options || "{}");
                    options.isHeaderField = true;
                    attrs.options = JSON.stringify(options);
                }
            });
            return false;
        });
        return formView.props({ ...genericProps, ir: marked }, view);
    },
};

registry.category("views").add("base_settings", settingsFormView);
