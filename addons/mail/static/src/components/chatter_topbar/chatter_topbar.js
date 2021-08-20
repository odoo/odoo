/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatterTopbar extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chatter}
     */
    get chatter() {
        return this.messaging && this.messaging.models['mail.chatter'].get(this.props.chatterLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAttachments(ev) {
        this.chatter.update({
            isAttachmentBoxVisible: !this.chatter.isAttachmentBoxVisible,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        this.trigger('o-close-chatter');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLogNote(ev) {
        if (!this.chatter.composer) {
            return;
        }
        if (this.chatter.isComposerVisible && this.chatter.composer.isLog) {
            this.chatter.update({ isComposerVisible: false });
        } else {
            this.chatter.showLogNote();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickScheduleActivity(ev) {
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t("Schedule Activity"),
            res_model: 'mail.activity',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: this.chatter.thread.id,
                default_res_model: this.chatter.thread.model,
            },
            res_id: false,
        };
        return owl.Component.env.bus.trigger('do-action', {
            action,
            options: {
                on_close: () => {
                    this.trigger('reload', { keepChanges: true });
                },
            },
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSendMessage(ev) {
        if (!this.chatter.composer) {
            return;
        }
        if (this.chatter.isComposerVisible && !this.chatter.composer.isLog) {
            this.chatter.update({ isComposerVisible: false });
        } else {
            this.chatter.showSendMessage();
        }
    }

}

Object.assign(ChatterTopbar, {
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ChatterTopbar',
});

registerMessagingComponent(ChatterTopbar);
