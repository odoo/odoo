/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "Start a meeting" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Discuss/onClickStartAMeetingButton
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    Discuss
        [Action/behavior]
            :meetingChannel
                {Thread/createGroupChat}
                    [default_display_mode]
                        video_full_screen
                    [partners_to]
                        {Env/currentPartner}
                        .{Partner/id}
            {Thread/toggleCall}
                [0]
                    @meetingChannel
                [1]
                    [startWithVideo]
                        true
            {Thread/open}
                [0]
                    @meetingChannel
                [1]
                    [focus]
                        false
            {if}
                {Record/exists}
                    @meetingChannel
                .{isFalsy}
                .{|}
                    @record
                    .{Discuss/threadView}
                    .{isFalsy}
            .{then}
                {break}
            {ThreadViewTopbar/openInvitePopoverView}
                @record
                .{Discuss/threadView}
                .{ThreadView/topbar}
`;
