import { Component, t, useProps } from "@odoo/owl";

import { onActivityChangedType } from "@mail/core/web/activity_types";
import { propSignal } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ActivityMailTemplate extends Component {
    static template = "mail.ActivityMailTemplate";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activity = propSignal("activity", t.instanceOf(this.store["mail.activity"]));
        this.onActivityChanged = useProps.static(
            "onActivityChanged",
            onActivityChangedType(this.store).optional()
        );
        this.onClickButtons = useProps.static(
            "onClickButtons",
            t.function([]).optional(() => () => {})
        );
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ activityAtRender: import("models").Activity, mailTemplate: Object }} param1
     */
    onClickPreview(ev, { activityAtRender, mailTemplate }) {
        ev.stopPropagation();
        ev.preventDefault();
        this.onClickButtons();
        const thread = activityAtRender.thread;
        const action = {
            name: _t("Compose Email"),
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_res_ids: [activityAtRender.res_id],
                default_model: activityAtRender.res_model,
                default_subtype_xmlid: "mail.mt_comment",
                default_template_id: mailTemplate.id,
                force_email: true,
            },
        };
        this.env.services.action.doAction(action, {
            onClose: () => this.onActivityChanged?.({ thread }),
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ activityAtRender: import("models").Activity, mailTemplate: Object }} param1
     */
    async onClickSend(ev, { activityAtRender, mailTemplate }) {
        ev.stopPropagation();
        ev.preventDefault();
        this.onClickButtons();
        const thread = activityAtRender.thread;
        await this.env.services.orm.call(activityAtRender.res_model, "activity_send_mail", [
            [activityAtRender.res_id],
            mailTemplate.id,
        ]);
        this.onActivityChanged?.({ thread });
    }
}
