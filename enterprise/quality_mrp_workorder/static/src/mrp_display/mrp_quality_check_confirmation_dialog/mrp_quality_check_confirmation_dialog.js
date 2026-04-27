import { patch } from "@web/core/utils/patch";
import { MrpQualityCheckConfirmationDialog } from "@mrp_workorder/mrp_display/dialog/mrp_quality_check_confirmation_dialog";

patch(MrpQualityCheckConfirmationDialog.prototype, {

    get shouldDisplayValidateButton() {
        if (this.recordData.test_type === "spreadsheet") {
            return false
        }
        return super.shouldDisplayValidateButton;
    },

    async openSpreadsheet() {
        this.state.disabled = true;
        const action = await this.props.record.model.orm.call(
            this.props.record.resModel,
            "action_open_spreadsheet",
            [this.props.record.resId],
        );
        this.props.close();
        action.params.pass_action = "action_pass_and_next";
        action.params.fail_action = "action_fail_and_next";
        await this.action.doAction(action);
    },
});
