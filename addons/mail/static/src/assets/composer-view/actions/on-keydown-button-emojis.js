/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/onKeydownButtonEmojis
        [Action/params]
            record
                [type]
                    ComposerView
            ev
                [type]
                    web.KeyboardEvent
        [Action/behavior]
            {if}
                @ev
                .{web.KeyboardEvent/key}
                .{=}
                    Escape
                .{&}
                    @record
                    .{ComposerView/emojisPopoverView}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ComposerView/doFocus]
                            true
                        [ComposerView/emojisPopoverView]
                            {Record/empty}
                {Event/markAsHandled}
                    [0]
                        @ev
                    [1]
                        Composer.closeEmojisPopover
`;
