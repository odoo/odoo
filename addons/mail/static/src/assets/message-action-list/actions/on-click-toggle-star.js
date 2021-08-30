/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageActionList/onClickToggleStar
        [Action/params]
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {Message/toggleStar}
                @record
                .{MessageActionList/message}
`;
