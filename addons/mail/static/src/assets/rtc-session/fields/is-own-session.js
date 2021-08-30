/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the session is a session of the current partner.
        This can be true for many sessions, as one user can have multiple
        sessions active across several tabs, browsers and devices.
        To determine if this session is the active session of this tab,
        use this.rtc instead.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isOwnSession
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{RtcSession/partner}
            .{&}
                {Env/currentPartner}
                .{=}
                    @record
                    .{RtcSession/partner}
            .{|}
                @record
                .{RtcSession/guest}
                .{&}
                    {Env/currentGuest}
                    .{=}
                        @record
                        .{RtcSession/guest}
`;
