/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "show member list" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onClickShowMemberList
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{ThreadViewTopbar/threadView}
                [1]
                    [ThreadView/isMemberListOpened]
                        true
`;
