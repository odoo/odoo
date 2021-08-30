/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/onClickHideMemberList
        [Action/params]
            chatWindow
                [type]
                    ChatWindow
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {Event/markAsHandled}
                [0]
                    @ev
                [1]
                    ChatWindow/onClickHideMemberList
            {Record/update}
                [0]
                    @chatWindow
                [1]
                    [ChatWindow/isMemberListOpened]
                        false
            {if}
                @chatWindow
                .{ChatWindow/threadViewer}
                .{ThreadViewer/threadView}
            .{then}
                {ThreadView/addComponentHint}
                    [0]
                        @chatWindow
                        .{ChatWindow/threadViewer}
                        .{ThreadViewer/threadView}
                    [1]
                        member-list-hidden
`;
