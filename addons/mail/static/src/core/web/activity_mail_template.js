import { Component, props, t } from "@odoo/owl";

import { propSignal } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ActivityMailTemplate extends Component {
    static template = "mail.ActivityMailTemplate";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activity = propSignal("activity", t.instanceOf(this.store["mail.activity"].Class));
        this.onActivityChanged = props.static(
            "onActivityChanged",
            t.function([t.instanceOf(this.store["mail.thread"].Class)]).optional()
        );
        this.onClickButtons = props.static(
            "onClickButtons",
            t.function([]).optional(() => () => {})
        );
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} mailTemplate
     */
    onClickPreview(ev, mailTemplate) {
        ev.stopPropagation();
        ev.preventDefault();
        this.onClickButtons();
        const action = {
            name: _t("Compose Email"),
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_res_ids: [this.activity().res_id],
                default_model: this.activity().res_model,
                default_subtype_xmlid: "mail.mt_comment",
                default_template_id: mailTemplate.id,
                force_email: true,
            },
        };
        const thread = this.store["mail.thread"].insert({
            model: this.activity().res_model,
            id: this.activity().res_id,
        });
        this.env.services.action.doAction(action, {
            onClose: () => this.onActivityChanged?.(thread),
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} mailTemplate
     */
    async onClickSend(ev, mailTemplate) {
        ev.stopPropagation();
        ev.preventDefault();
        this.onClickButtons();
        const thread = this.store["mail.thread"].insert({
            model: this.activity().res_model,
            id: this.activity().res_id,
        });
        await this.env.services.orm.call(this.activity().res_model, "activity_send_mail", [
            [this.activity().res_id],
            mailTemplate.id,
        ]);
        this.onActivityChanged?.(thread);
    }
}
