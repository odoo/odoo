odoo.define('mail.messaging.component.ChatterTopbar', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class ChatterTopbar extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const chatter = this.env.entities.Chatter.get(props.chatterLocalId);
            const thread = chatter ? chatter.thread : undefined;
            const threadAttachments = thread ? thread.allAttachments : [];
            return {
                areThreadAttachmentsLoaded: thread && thread.areAttachmentsLoaded,
                chatter,
                threadAttachmentsAmount: threadAttachments.length,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Chatter}
     */
    get chatter() {
        return this.env.entities.Chatter.get(this.props.chatterLocalId);
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
    _onClickFollow(ev) {
        // TODO
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFollowers(ev) {
        // TODO
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLogNote(ev) {
        if (this.chatter.isComposerVisible && this.chatter.isComposerLog) {
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
                default_res_id: this.chatter.threadId,
                default_res_model: this.chatter.threadModel,
            },
            res_id: false,
        };
        return this.env.do_action(action, {
            // A bit "extreme", could be improved:
            // normally only an activity is created (no update nor delete)
            on_close: () => this.chatter.refreshActivities(),
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSendMessage(ev) {
        if (this.chatter.isComposerVisible && !this.chatter.isComposerLog) {
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
    template: 'mail.messaging.component.ChatterTopbar',
});

return ChatterTopbar;

});
