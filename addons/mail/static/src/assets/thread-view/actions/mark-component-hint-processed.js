/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadView/markComponentHintProcessed
        [Action/params]
            threadView
                [type]
                    ThreadView
            hint
                [type]
                    Hint
        [Action/behavior]
            {Record/update}
                [0]
                    @threadView
                [1]
                    [ThreadView/componentHintList]
                        @threadView
                        .{ThreadView/componentHintList}
                        .{Collection/filter}
                            {Record/insert}
                                [Record/models]
                                    Function
                                [Function/in]
                                    item
                                [Function/out]
                                    @item
                                    .{!=}
                                        @hint
            {Env/messagingBus}
            .{Bus/trigger}
                [0]
                    o-thread-view-hint-processed
                [1]
                    [hint]
                        @hint
                    [threadViewer]
                        @threadView
                        .{ThreadView/threadViewer}
`;
