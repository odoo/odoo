/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageActionListComponent
        [Model/fields]
            messageActionList
        [Model/template]
            root
                actionReaction
                reactionPopoverView
                actionStar
                actionReply
                actionMarkAsRead
                actionEdit
                actionDelete
`;
