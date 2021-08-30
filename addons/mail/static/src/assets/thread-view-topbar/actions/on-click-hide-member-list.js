/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "hide member list" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onClickHideMemberList
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
                        false
            {ThreadView/addComponentHint}
                [0]
                    @record
                    .{ThreadViewTopbar/threadView}
                [1]
                    member-list-hidden
`;
