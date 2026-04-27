/** @odoo-module */

import { useState, onMounted, onPatched } from "@odoo/owl";
import { formView } from "@web/views/form/form_view";
import { useModelConfigFetchInvisible } from "@web_studio/client_action/view_editor/editors/utils";

/**
 * This hook ensures that a record datapoint has the "parent" key in its evalContext, allowing
 * to access to field values of the parent record. This is useful in Studio because an x2many
 * record can be opened, but in a standalone fashion. It will be the root of its model, even
 * though, in practice, there's a parent record and a parent form view. This allows snippets like
 * `<field name="..." invisible="not parent.id" />` in the child view to work.
 */
function useExternalParentInModel(model, parentRecord) {
    model._createRoot = (config, data) => {
        return new model.constructor.Record(model, config, data, { parentRecord });
    };
}

export class FormEditorController extends formView.Controller {
    static props = {
        ...formView.Controller.props,
        parentRecord: { type: [Object, { value: null }], optional: true },
    };

    setup() {
        super.setup();
        useModelConfigFetchInvisible(this.model);
        this.mailTemplate = null;
        this.hasFileViewerInArch = false;

        this.viewEditorModel = useState(this.env.viewEditorModel);

        if (this.props.parentRecord) {
            useExternalParentInModel(this.model, this.props.parentRecord);
        }

        onMounted(() => {
            const xpath = this.viewEditorModel.lastActiveNodeXpath;
            if (xpath && xpath.includes("notebook")) {
                const tabXpath = xpath.match(/.*\/page\[\d+\]/)[0];
                const tab = document.querySelector(`[data-studio-xpath='${tabXpath}'] a`);
                if (tab) {
                    // store the targetted element to restore it after being patched
                    this.notebookElementData = {
                        xpath,
                        restore: Boolean(this.viewEditorModel.activeNodeXpath),
                        sidebarTab: this.viewEditorModel.sidebarTab,
                        isTab: xpath.length === tabXpath.length,
                    };
                    tab.click();
                }
            } else {
                this.notebookElementData = null;
            }
        });

        onPatched(() => {
            if (this.notebookElementData) {
                if (
                    this.notebookElementData.isTab &&
                    this.viewEditorModel.lastActiveNodeXpath !== this.notebookElementData.xpath
                ) {
                    return;
                }
                if (this.notebookElementData.restore) {
                    this.env.config.onNodeClicked(this.notebookElementData.xpath);
                } else {
                    // no element was currently highlighted, the editor sidebar must display the stored tab
                    this.viewEditorModel.resetSidebar(this.notebookElementData.sidebarTab);
                }
                this.notebookElementData = null;
            }
        });
    }

    beforeUnload() {}

    _shouldUseSubEnv() {
        return false;
    }
}
