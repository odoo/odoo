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
        getAvailableResModels(null, this.orm).then((models) => (this.state.models = models));
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
                        /* Changing the model linked to the activity also changes available activity types.
                         * This in turn triggers a recompute of all fields dependent on activity types, including
                         * summary and notes, which may already have been edited (especially summary as the user is
                         * likely to fill out the wizard in order).
                         * To prevent this, current summary and notes are saved and will be recovered after the model
                         * has been changed.
                         */
                        const persistDataThroughModelChange = {
                            summary: this.props.record.data.summary,
                            note: this.props.record.data.note,
                        };

                        await this.props.record.update(
                            {
                                res_model: this.state.resModel,
                                res_ids: resId,
                            },
                            { save: false }
                        );
                        const recordInfo = await this.orm.call(
                            this.state.resModel,
                            "name_search",
                            [],
                            {
                                domain: [["id", "in", resId]],
                            }
                        );
                        this.state.resModelName = recordInfo[0][1];

                        // recover saved inputs
                        this.props.record.update(persistDataThroughModelChange);
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
        // information to persist current summary and notes through model_id changes
        const persistDataThroughModelChange = {
            summary: this.props.record.data.summary,
            note: this.props.record.data.note,
        };
        this.props.record.update({
            res_model: false,
            res_ids: false,
        });
        this.props.record.update(persistDataThroughModelChange);
        return this.onModelSelected({ technical: false, label: false });
    }
}

registry.category("fields").add("activity_model_selector", {
    component: ActivityModelSelector,
});
