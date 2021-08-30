/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Stops editing this message.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageView/stopEditing
        [Action/params]
            record
                [type]
                    MessageView
        [Action/behavior]
            {if}
                @record
                .{MessageView/threadView}
                .{&}
                    @record
                    .{MessageView/threadView}
                    .{ThreadView/composerView}
                .{&}
                    {Device/isMobileDevice}
                    .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{MessageView/threadView}
                        .{ThreadView/composerView}
                    [1]
                        [ComposerView/doFocus]
                            true
            {Record/update}
                [0]
                    @record
                [1]
                    [MessageView/composerForEditing]
                        {Record/empty}
                    [MessageView/composerViewInEditing]
                        {Record/empty}
`;
