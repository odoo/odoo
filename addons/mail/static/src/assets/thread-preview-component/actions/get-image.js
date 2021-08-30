/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Get the image route of the thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadPreviewComponent/getImage
        [Action/params]
            record
                [type]
                    ThreadPreviewComponent
        [Action/returns]
            String
        [Action/behavior]
            {if}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/correspondent}
            .{then}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/correspondent}
                .{Partner/avatarUrl}
            .{else}
                /web/image/mail.channel/
                .{+}
                    @record
                    .{ThreadPreviewComponent/threadPreviewView}
                    .{ThreadPreviewView/thread}
                    .{Thread/id}
                .{+}
                    /avatar_128?unique=
                .{+}
                    @record
                    .{ThreadPreviewComponent/threadPreviewView}
                    .{ThreadPreviewView/thread}
                    .{Thread/avatarCacheKey}
`;
