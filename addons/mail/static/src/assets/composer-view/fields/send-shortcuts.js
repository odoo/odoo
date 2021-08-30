/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Keyboard shortcuts from text input to send message.
        The format is an array of string that can contain 'enter',
        'ctrl-enter', and/or 'meta-enter'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            sendShortcuts
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            Collection<String>
        [Field/compute]
            {if}
                @record
                .{ComposerView/chatter}
            .{then}
                ctrl-enter
                meta-enter
            .{elif}
                @record
                .{ComposerView/messageViewInEditing}
            .{then}
                enter
            .{elif}
                @record
                .{ComposerView/threadView}
            .{then}
                {Dev/comment}
                    Actually in mobile there is a send button, so we need there 'enter' to allow new
                    line. Hence, we want to use a different shortcut 'ctrl/meta enter' to send for
                    small screen size with a non-mailing channel. Here send will be done on clicking
                    the button or using the 'ctrl/meta enter' shortcut.
                {if}
                    {Device/isMobile}
                    .{|}
                        {Discuss/threadView}
                        .{=}
                            @record
                            .{ComposerView/threadView}
                        .{&}
                            {Discuss/thread}
                            .{=}
                                {Env/inbox}
                .{then}
                    ctrl-enter
                    meta-enter
                .{else}
                    enter
`;
