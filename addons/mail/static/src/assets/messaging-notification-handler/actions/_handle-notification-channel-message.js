/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationChannelMessage
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            id
                [type]
                    Integer
                [as]
                    channelId
            message
                [type]
                    Object
                [as]
                    messageData
        [Action/behavior]
            :channel
                {Record/findById}
                    [Thread/id]
                        @channelId
                    [Thread/model]
                        mail.channel
            {if}
                @notificationHandler
                .{MessagingNotificationHandler/channel}
                .{isFalsy}
                .{&}
                    {Env/isCurrentUserGuest}
            .{then}
                {Dev/comment}
                    guests should not receive messages for channels they don't know, and they can't make the channel_info RPC
                {break}
            :convertedData
                {Message/convertData}
                    @messageData
            {Dev/comment}
                Fetch missing info from channel before going further. Inserting
                a channel with incomplete info can lead to issues. This is in
                particular the case with the 'uuid' field that is assumed
                "required" by the rest of the code and is necessary for some
                features such as chat windows.
            {if}
                @channel
                .{isFalsy}
            .{then}
                :channel
                    {Record/doAsync}
                        [0]
                            @notificationHandler
                        [1]
                            {Thread/performRpcChannelInfo}
                                [ids]
                                    @channelId
                            .{Collection/first}
            {if}
                @channel
                .{Thread/isPinned}
                .{isFalsy}
            .{then}
                {Thread/pin}
                    @channel
            :message
                {Record/insert}
                    [Record/models]
                        Message
                    @convertedData
            {MessagingNotificationHandler/_notifyThreadViewsMessageReceived}
                [0]
                    @notificationHandler
                [1]
                    @message
            {Dev/comment}
                If the current partner is author, do nothing else.
            {if}
                @message
                .{Message/author}
                .{=}
                    {Env/currentPartner}
            .{then}
                {break}
            {Dev/comment}
                In all other cases: update counter and notify if necessary.
                Chat from OdooBot is considered disturbing and should only be
                shown on the menu, but no notification and no thread open.
            :isChatWithOdooBot
                @channel
                .{Thread/correspondent}
                .{&}
                    @channel
                    .{Thread/correspondent}
                    .{=}
                        {Env/partnerRoot}
            {if}
                @isChatWithOdooBot
                .{isFalsy}
            .{then}
                :isOdooFocused
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        bus_service
                    .{Dict/get}
                        isOdooFocused
                    .{Function/call}
                {Dev/comment}
                    Notify if out of focus
                {if}
                    @isOdooFocused
                    .{isFalsy}
                    .{&}
                        @channel
                        .{Thread/isChatChannel}
                {then}
                    {MessagingNotificationHandler/_notifyNewChannelMessageWhileOutOfFocus}
                        [0]
                            @notificationHandler
                        [1]
                            [channel]
                                @channel
                            [message]
                                @message
                {if}
                    @channel
                    .{Thread/model}
                    .{=}
                        mail.channel
                    .{&}
                        @channel
                        .{Thread/channelType}
                        .{!=}
                            channel
                    .{&}
                        {Env/currentGuest}
                        .{isFalsy}
                .{then}
                    {Dev/comment}
                        disabled on non-channel threads and
                        on 'channel' channels for performance reasons
                    {Thread/markAsFetched}
                        @channel
                {Dev/comment}
                    open chat on receiving new message if it was not already opened or folded
                {if}
                    @channel
                    .{Thread/channelType}
                    .{!=}
                        channel
                    .{&}
                        {Device/isMobile}
                        .{isFalsy}
                    .{&}
                        @channel
                        .{Thread/chatWindow}
                        .{isFalsy}
                .{then}
                    {ChatWindowManager/openThread}
                        @channel
`;
