odoo.define('mail/static/src/components/message_actions/message_actions.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const useUpdate = require('mail/static/src/component_hooks/use_update/use_update.js');
const { Component, useState } = owl;

class MessageAction extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            // Open the delete confirmation dialog
            hasDeleteConfirmDialog: false,
        });
        useStore(props => {
            const message = this.env.models['mail.message'].get(props.messageLocalId);
            return {
                message: message ? message.__state : undefined,
            };
        });
        useUpdate({ func: () => this._update() });
        /**
         * The intent of the reply button depends on the last rendered state.
         */
        this._wasSelected;
    }

    /**
     * @returns {mail.message}
     */
    get message() {
        return this.env.models['mail.message'].get(this.props.messageLocalId);
    }

    /**
     * @private
     */
    _update() {
        this._wasSelected = this.props.isSelected;
    }

    /**
     * Is the user allowed to delete a message
     * @private
     */
    _allowDelete() {
        return this.message.author.id == this.env.messaging.currentUser.partner.id
            || this.env.session.is_admin;
    }

    /**
     * Is the user allowed to star this message
     * @private
     */
    _allowStar() {
        return !this.message.isTemporary &&
            ((this.message.message_type !== 'notification' && this.message.originThread && this.message.originThread.model === 'mail.channel') || !this.message.isTransient) &&
            this.message.moderation_status !== 'pending_moderation';
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        ev.stopPropagation();
        this.message.markAsRead();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickStar(ev) {
        ev.stopPropagation();
        this.message.toggleStar();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickReply(ev) {
        // Use this._wasSelected because this.props.isSelected might be changed
        // by a global capture click handler (for example the one from Composer)
        // before the current handler is executed. Indeed because it does a
        // toggle it needs to take into account the value before the click.
        if (this._wasSelected) {
            this.env.messaging.discuss.clearReplyingToMessage();
        } else {
            this.message.replyTo();
        }
    }

    /**
     * @private
     */
    _onDeleteMessage() {
        this.state.hasDeleteConfirmDialog = true;
    }

    /**
     * @private
     */
    _onDeleteConfirmDialogClosed() {
        this.state.hasDeleteConfirmDialog = false;
    }
}

Object.assign(MessageAction, {
    defaultProps: {
        hasMarkAsReadIcon: false,
        hasReplyIcon: false,
        isSelected: false,
    },
    props: {
        hasMarkAsReadIcon: Boolean,
        hasReplyIcon: Boolean,
        isSelected: Boolean,
        messageLocalId: String,
    },
    template: 'mail.MessageActions',
});

return MessageAction;

});
