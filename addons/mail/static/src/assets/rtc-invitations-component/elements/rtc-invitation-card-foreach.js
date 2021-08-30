/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            rtcInvitationCardForeach
        [Element/model]
            RtcInvitationsComponent
        [Field/target]
            RtcInvitationsComponent:rtcInvitationCard
        [Record/models]
            Foreach
        [Foreach/collection]
            {Env/ringingThreads}
        [Foreach/as]
            thread
        [Element/key]
            @field
            .{Foreach/get}
                thread
            .{Record/id}
        [RtcInvitationsComponent:rtcInvitationCard/thread]
            @field
            .{Foreach/get}
                thread
`;
