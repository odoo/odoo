import { useState } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";

export class FormControllerWithHTMLExpander extends FormController {
    static template = "resource.FormViewWithHtmlExpander";

    setup() {
        super.setup();
        this.htmlExpanderState = useState({ reload: true });
        const oldOnNotebookPageChange = this.onNotebookPageChange;
        this.onNotebookPageChange = (notebookId, page) => {
            oldOnNotebookPageChange(notebookId, page);
            if (page && !this.htmlExpanderState.reload) {
                this.htmlExpanderState.reload = true;
            }
        };
    }

    get modelParams() {
        const modelParams = super.modelParams;
        const onRootLoaded = modelParams.hooks.onRootLoaded;
        modelParams.hooks.onRootLoaded = async () => {
            if (onRootLoaded) {
                onRootLoaded();
            }
            this.htmlExpanderState.reload = true;
        };
        return modelParams;
    }

    notifyHTMLFieldExpanded() {
        this.htmlExpanderState.reload = false;
    }

    async onRecordSaved(record, changes) {
        super.onRecordSaved(record, changes);
        this.htmlExpanderState.reload = true;
    }
}
