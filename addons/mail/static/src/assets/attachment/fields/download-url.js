/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            downloadUrl
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Attachment/accessToken}
                .{isFalsy}
                .{&}
                    @record
                    .{Attachment/originThread}
                .{&}
                    @record
                    .{Attachment/originThread}
                    .{Thread/model}
                    .{=}
                        mail.channel
            .{then}
                /mail/channel/
                .{+}
                    @record
                    .{Attachment/originThread}
                    .{Thread/id}
                .{+}
                    /attachment/
                .{+}
                    @record
                    .{Attachment/id}
            .{else}
                :accessToken
                    {if}
                        @record
                        .{Attachment/accessToken}
                    .{then}
                        ?access_token=
                        .{+}
                            @record
                            .{Attachment/accessToken}
                    .{else}
                            
                /web/content/ir.attachment/
                .{+}
                    @record
                    .{Attachment/id}
                .{+}
                    /datas
                .{+}
                    @accessToken
`;
