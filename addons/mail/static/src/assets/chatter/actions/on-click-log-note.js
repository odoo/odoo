/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/onClickLogNote
        [Action/params]
            record
                [type]
                    Chatter
        [Action/behavior]
            {if}
                @record
                .{Chatter/composerView}
                .{&}
                    @record
                    .{Chatter/composerView}
                    .{ComposerView/composer}
                    .{Composer/isLog}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [Chatter/composerView]
                            {Record/empty}
            .{else}
                {Chatter/showLogNote}
                    @record
`;
