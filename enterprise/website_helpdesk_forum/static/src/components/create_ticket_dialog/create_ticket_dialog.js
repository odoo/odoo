import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { escape, sprintf } from "@web/core/utils/strings";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, markup, useRef } from "@odoo/owl";

export class CreateTicketDialog extends Component {
    static template = "website_helpdesk_forum.CreateTicketDialog";
    static components = { Dialog };
    static props = {
        forumId: { type: Number, optional: false },
        postId: { type: Number, optional: false },
        close: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({});
        this.inputText = useRef("inputText");
        this.notification = useService("notification");
        this.orm = useService("orm");

        onWillStart(async () => {
            const forumPostData = await rpc(window.location.href + "/get-forum-data");
            this.state.data = {
                ...forumPostData,
                team_id: forumPostData.teams?.[0]?.[0],
            };
        });
    }

    _createTicket() {
        return this.orm.call('forum.forum', 'create_ticket', [
            this.props.forumId,
            this.props.postId,
            this.state.data,
        ]);
    }

    _checkInputIsValid() {
        const isValid = this.inputText.el.value.trim().length;
        this.inputText.el.classList.toggle('is-invalid', !isValid);
        return isValid;
    }

    async onCreateTicket() {
        if (!this._checkInputIsValid()) {
            return;
        }
        const response = await this._createTicket();
        const message = markup(sprintf(
            escape(_t('Helpdesk ticket %s has been successfully created for this forum post.')),
            `<b>#${escape(response.ticket)}</b>`,
        ));
        this.notification.add(message, { type: "success" });
        this.props.close();
    }

    async onCreateAndViewTicket() {
        if (!this._checkInputIsValid()) {
            return;
        }
        const response = await this._createTicket();
        window.open(response.url, '_blank');
        this.props.close();
    }
}
