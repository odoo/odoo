import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { memoize } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { ModelSelector } from "@web/core/model_selector/model_selector";
import { registry } from "@web/core/registry";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/** largely taken from documents' DocumentsDetailPanel, which selects arbitrary models and records
  * through two interactions:
  * 1- select the model through a list of accesible and appropriate models (getAvailableResModels)
  * 2- select one of this model's records through a tree view in a new dialog that opens
  **/

// Small hack, memoize uses the first argument as cache key, but we need the orm which will not be the same.
const getAvailableResModels = memoize((_null, orm) =>
    orm.call("mail.activity.schedule", "get_model_options")
);

class ActivityModelSelector extends Component {

    static components = { ModelSelector };
    static template = "mail.ActivityModelSelector";
    static props = standardFieldProps;

    setup() {
        // Use a state for the model to not write on the record the model without record id
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({
            resModel: this.props.record.data.res_model,
            resModelName: this.props.record.data.res_model_name || "",
            models: [],
        });
        getAvailableResModels(null, this.orm).then((models) => (
            this.state.models = models
        ));
    }

    async onModelSelected(value) {
        this.state.resModel = value.technical;
        this.state.resModelName = value.label || "";
        if (this.state.resModel) {
            this.dialog.add(
                SelectCreateDialog,
                {
                    title: _t("Select a Record To Link"),
                    noCreate: true,
                    multiSelect: false,
                    resModel: this.state.resModel,
                    onSelected: async (resId) => {
                        await this.props.record.update({
                            res_model: this.state.resModel,
                            res_ids: resId,
                        }, { save: false })
                        const record = await this.orm.read(
                            this.props.record.data.res_model,
                            this.props.record.data.res_ids,
                            ['name']
                        )
                        this.state.resModelName = record[0].name;
                    },
                },
                {
                    onClose: () => {
                        if (!this.props.record.data.res_ids) {
                            this.onRecordReset();
                        }
                    },
                }
            );
        }
    }

    onRecordReset() {
        this.props.record.update({
            res_model: false,
            res_ids: false,
        })
        return this.onModelSelected({ technical: false, label: false });
    }
}

registry.category("fields").add("activity_model_selector", {
    component: ActivityModelSelector
})
