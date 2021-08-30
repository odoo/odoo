/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Discards the composer when clicking away.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/onClickCaptureGlobal
        [Action/params]
            record
                [type]
                    ComposerView
            ev
                [type]
                    web.MouseEvent
        [Action/behavior]
            {if}
                {PopoverView/contains}
                    [0]
                        @record
                    [1]
                        @ev
                        .{web.Event/target}
            .{then}
                {break}
            {Dev/comment}
                Let event be handled by bubbling handlers first
            {Browser/setTimeout}
            {if}
                {Event/isHandled}
                    [0]
                        @ev
                    [1]
                        MessageActionList.replyTo
            .{then}
                {break}
            {ComposerView/discard}
                @record
`;
