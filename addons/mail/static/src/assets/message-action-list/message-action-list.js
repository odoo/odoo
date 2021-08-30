/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageActionList
        [Model/fields]
            actionReactionRef
            deleteConfirmDialog
            hasMarkAsReadIcon
            hasReplyIcon
            message
            messageView
            reactionPopoverView
        [Model/id]
            MessageActionList/messageView
        [Model/actions]
            MessageActionList/onClick
            MessageActionList/onClickActionReaction
            MessageActionList/onClickDelete
            MessageActionList/onClickEdit
            MessageActionList/onClickMarkAsRead
            MessageActionList/onClickReaction
            MessageActionList/onClickReplyTo
            MessageActionList/onClickToggleStar
`;
