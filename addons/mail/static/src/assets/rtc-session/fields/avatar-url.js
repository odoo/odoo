/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The relative url of the image that represents the session.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            avatarUrl
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{RtcSession/channel}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{RtcSession/partner}
            .{then}
                /mail/channel/
                .{+}
                    @record
                    .{RtcSession/channel}
                    .{Thread/id}
                .{+}
                    /partner/
                .{+}
                    @record
                    .{RtcSession/partner}
                    .{Partner/id}
                .{+}
                    /avatar_128
            .{elif}
                @record
                .{RtcSession/guest}
            .{then}
                /mail/channel/
                .{+}
                    @record
                    .{RtcSession/channel}
                    .{Thread/id}
                .{+}
                    /guest/
                .{+}
                    @record
                    .{RtcSession/guest}
                    .{Thread/id}
                {+}
                    /avatar_128?unique=
                .{+}
                    @record
                    .{RtcSession/guest}
                    .{Guest/name}
`;
