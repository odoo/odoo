/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/onClickSendMessage
        [Action/params]
            record
                [type]
                    Chatter
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {if}
                @record
                .{Chatter/composerView}
                .{&}
                    @record
                    .{Chatter/composerView}
                    .{ComposerView/composer}
                    .{Composer/isLog}
                    .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [Chatter/composerView]
                            {Record/empty}
            .{else}
                {Chatter/showSendMessage}
                    @record
`;
