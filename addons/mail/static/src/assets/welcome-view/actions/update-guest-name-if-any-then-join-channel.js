/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Adds the current guest to members of the channel linked to this
        welcome view.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/updateGuestNameIfAnyThenJoinChannel
        [Action/params]
            record
                [type]
                    WelcomeView
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [route]
                    /mail/channel/add_guest_as_member
                [params]
                    [channel_id]
                        @record
                        .{WelcomeView/channel}
                        .{Thread/id}
                    [channel_uuid]
                        @record
                        .{WelcomeVIew/channel}
                        .{Thread/uuid}
`;
