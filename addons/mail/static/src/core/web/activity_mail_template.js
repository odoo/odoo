import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("models").Activity} activity
 * @property {function} [onClickButtons]
 * @property {function} [onActivityChanged]
 * @extends {Component<Props, Env>}
 */
export class ActivityMailTemplate extends Component {
    static defaultProps = {
        onClickButtons: () => {},
    };
    static props = ["activity", "onClickButtons?", "onActivityChanged?"];
    static template = "mail.ActivityMailTemplate";

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} mailTemplate
     */
    onClickPreview(ev, mailTemplate) {
        ev.stopPropagation();
        ev.preventDefault();
        this.props.onClickButtons();
        const action = {
            name: _t("Compose Email"),
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_res_ids: [this.props.activity.res_id],
                default_model: this.props.activity.res_model,
                default_subtype_xmlid: "mail.mt_comment",
                default_template_id: mailTemplate.id,
                force_email: true,
            },
        };
        const thread = this.store.Thread.insert({
            model: this.props.activity.res_model,
            id: this.props.activity.res_id,
        });
        this.env.services.action.doAction(action, {
            onClose: () => this.props.onActivityChanged?.(thread),
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} mailTemplate
     */
    async onClickSend(ev, mailTemplate) {
        ev.stopPropagation();
        ev.preventDefault();
        this.props.onClickButtons();
        const thread = this.store.Thread.insert({
            model: this.props.activity.res_model,
            id: this.props.activity.res_id,
        });
        await this.env.services.orm.call(this.props.activity.res_model, "activity_send_mail", [
            [this.props.activity.res_id],
            mailTemplate.id,
        ]);
        this.props.onActivityChanged?.(thread);
    }
}
