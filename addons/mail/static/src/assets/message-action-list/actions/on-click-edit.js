/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageActionList/onClickEdit
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    MessageActionList
        [Action/behavior]
            {MessageView/startEditing}
                @record
                .{MessageActionList/messageView}
`;
