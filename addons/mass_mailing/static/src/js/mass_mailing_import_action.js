import { registry } from "@web/core/registry";
import { ImportAction } from "@base_import/import_action/import_action";
export class MassMailingImportAction extends ImportAction {
    setup() {
        super.setup();
        // this.props.action.params.model is there for retro-compatiblity issues
        this.resModel = this.props.action.params.model || this.props.action.params.active_model;
        if (this.resModel) {
            this.props.updateActionState({ active_model: this.resModel });
        }
    }

    onWillStart() {
        this.model.setResModel(this.resModel);
        return this.model.init();
    }
};
registry.category("actions").add("action_import_mailing_contacts", MassMailingImportAction);
