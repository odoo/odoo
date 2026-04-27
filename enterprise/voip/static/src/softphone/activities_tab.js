import { Component, onMounted, useState } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";

export class ActivitiesTab extends Component {
    static props = { activities: { type: Array }, extraClass: { type: String, optional: true } };
    static defaultProps = { extraClass: "" };
    static template = "voip.ActivitiesTab";

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.voip = useState(useService("voip"));
        onMounted(() => this.voip.fetchTodayCallActivities());
        this.state = useState({ hoveredActivity: null });
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Activity} activity
     */
    onClickActivity(ev, activity) {
        if (isEventHandled(ev, "Activity.cancel")) {
            return;
        }
        this.voip.softphone.selectCorrespondence({ activity });
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Activity} activity
     */
    onClickCancelActivity(ev, activity) {
        markEventHandled(ev, "Activity.cancel");
        this.dialog.add(ConfirmationDialog, {
            title: _t("Hold on!"),
            body: _t(
                "Are you sure you want to delete this activity? It will be lost forever, which is quite a long time 😔"
            ),
            cancel() {},
            confirm: async () => {
                await this.orm.call("mail.activity", "unlink", [[activity.id]]);
                activity.remove();
            },
            confirmLabel: _t("Yes, do it."),
            cancelLabel: _t("Missclicked, sorry."),
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Activity} activity
     */
    onMouseEnterActivity(ev, activity) {
        this.state.hoveredActivity = activity.id;
    }

    /** @param {MouseEvent} ev */
    onMouseLeaveActivity(ev) {
        this.state.hoveredActivity = null;
    }
}
