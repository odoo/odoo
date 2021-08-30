/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the reaction icon.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageActionList/onClickReaction
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    MessageActionList
        [Action/behavior]
            {Message/addReaction}
                [0]
                    @record
                    .{MessageActionList/message}
                [1]
                    @ev
                    .{web.MouseEvent/currentTarget}
                    .{web.Element/dataset}
                    .{web.Dataset/get}
                        unicode
            {Record/update}
                [0]
                    @record
                [1]
                    [MssageActionList/reactionPopoverView]
                        {Record/empty}
`;
