/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether current session is unable to speak.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMute
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{RtcSession/isSelfMuted}
            .{|}
                @record
                .{RtcSession/isDeaf}
`;
