/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Name of the session, based on the partner name if set.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            name
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{RtcSession/partner}
            .{then}
                @record
                .{RtcSession/partner}
                .{Partner/name}
            {if}
                @record
                .{RtcSession/guest}
            .{then}
                @record
                .{RtcSession/guest}
                .{Guest/name}
`;
