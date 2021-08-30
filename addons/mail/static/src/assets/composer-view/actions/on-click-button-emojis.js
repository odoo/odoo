/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the emojis button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/onClickButtonEmojis
        [Action/params]
            record
                [type]
                    ComposerView
            ev
                [type]
                    web.MouseEvent
        [Action/behavior]
            {if}
                @record
                .{ComposerView/emojisPopoverView}
                .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ComposerView/emojisPopoverView]
                            {Record/insert}
                                [Record/models]
                                    PopoverView
            .{else}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ComposerView/emojisPopoverView]
                            {Record/empty}
`;
