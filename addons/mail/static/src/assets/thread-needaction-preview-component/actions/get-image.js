/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Get the image route of the thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadNeedactionPreviewComponent/getImage
        [Action/params]
            record
                [type]
                    ThreadNeedactionPreviewComponent
        [Action/returns]
            String
        [Action/behavior]
            {if}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/moduleIcon}
            .{then}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/moduleIcon}
            .{elif}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/correspondent}
            .{then}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/correspondent}
                .{Partner/avatarUrl}
            .{elif}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/model}
                .{=}
                    mail.channel
            .{then}
                /web/image/mail.channel/
                .{+}
                    @record
                    .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                    .{ThreadNeedactionPreviewView/thread}
                    .{Thread/id}
                .{+}
                    /avatar_128?unique=
                .{+}
                    @record
                    .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                    .{ThreadNeedactionPreviewView/thread}
                    .{Thread/avatarCacheKey}
            .{else}
                /mail/static/src/img/smiley/avatar.jpg
`;
