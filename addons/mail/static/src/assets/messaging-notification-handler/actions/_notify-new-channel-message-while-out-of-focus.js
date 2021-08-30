/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_notifyNewChannelMessageWhileOutOfFocus
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            channel
                [type]
                    Thread
            message
                [type]
                    Message
        [Action/behavior]
            {if}
                @message
                .{Message/author}
                .{isFalsy}
            .{then}
                :notificationTitle
                    {Locale/text}
                        New message
            .{else}
                {if}
                    @channel
                    .{Thread/channelType}
                    .{=}
                        channel
                .{then}
                    {Dev/comment}
                        hack: notification template does not support OWL
                        components, so we simply use their template to
                        make HTML as if it comes from component
                    :channelIcon
                        {Render/toString}
                            ThreadIconComponent
                                [0]
                                    @env
                                [1]
                                    [ThreadIconComponent/thread]
                                        @channel
                    :notificationTitle
                        {String/sprintf}
                            [0]
                                {Locale/text}
                                    %s from %s
                            [1]
                                @message
                                .{Message/author}
                                .{Partner/nameOrDisplayName}
                            [2]
                                @channelIcon
                                .{+}
                                    @channel
                                    .{Thread/displayName}
                .{else}
                    :notificationTitle
                        @message
                        .{Message/author}
                        .{Partner/nameOrDisplayName}
            :notificationContent
                {String/escape}
                    {Utils/htmlToTextContentInline}
                        @message
                        .{Message/body}
                    .{String/substr}
                        0
                        350
                        {Dev/comment}
                            optimal for native English speakers
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                bus_service
            .{Dict/get}
                sendNotification
            .{Function/call}
                [message]
                    @notificationContent
                [title]
                    @notificationTitle
                [type]
                    info
            {Record/update}
                [0]
                    @env
                [1]
                    [Env/outOfFocusUnreadMessageCounter]
                        {Field/add}
                            1
            :titlePattern
                {if}
                    {Env/outOfFocusUnreadMessageCounter}
                    .{=}
                        1
                .{then}
                    {Locale/text}
                        %d Message
                .{else}
                    {Locale/text}
                        %d Messages
            @env
            .{Env/owlEnv}
            .{Dict/get}
                bus
            .{Dict/get}
                trigger
            .{Function/call}
                [0]
                    set_title_part
                [1]
                    [part]
                        _chat
                    [title]
                        {String/sprintf}
                            [0]
                                @titlePattern
                            [1]
                                {Env/outOfFocusUnreadMessageCounter}
`;
