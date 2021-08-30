/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/onClickEmoji
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
                .{ComposerView/textInputComponent}
            .{then}
                {ComposerTextInputComponent/saveStateInStore}
                    @record
                    .{ComposerView/textInputComponent}
            {ComposerView/insertIntoTextInput}
                [0]
                    @record
                [1]
                    @ev
                    .{web.Event/currentTarget}
                    .{web.Element/dataset}
                    .{web.Dataset/get}
                        unicode
            {if}
                {Device/isMobileDevice}
                .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ComposerView/doFocus]
                            true
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerView/emojisPopoverView]
                        {Record/empty}
`;
