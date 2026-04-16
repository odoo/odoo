import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ActionDialog } from "@web/webclient/actions/action_dialog";


patch(ActionDialog.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    async dismiss() {
        try {
            await this.handleDialogClose();
        } catch (e) {
            console.error("Error during nemhandel dialog close:", e);
        }
        return super.dismiss();
    },

    async handleDialogClose() {
        const { resModel, resId } = this.props.actionProps || {};
        if (resModel === 'nemhandel.registration' && resId) {
            const records = await this.orm.search(
                resModel,
                [
                    ['id', '=', resId],
                    ['l10n_dk_nemhandel_proxy_state', '!=', 'in_verification']
                ],
                {limit: 1}
            );
            if (records.length) {
                await this.orm.call(
                    resModel,
                    "button_deregister_nemhandel_participant",
                    [[resId]]
                );
            }
        }
    }
});
