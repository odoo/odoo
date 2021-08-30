/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingInitializer/_initChannels
        [Action/params]
            messagingInitializer
                [type]
                    MessagingInitializer
            channelsData
                [type]
                    Collection<Object>
        [Action/behavior]
            {Utils/executeGracefully}
                @channelsData
                .{Collection/map}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            :convertedData
                                {Thread/convertData}
                                    @item
                            {if}
                                @convertedData
                                .{Dict/get}
                                    Thread/members
                                .{isFalsy}
                            .{then}
                                {Dev/comment}
                                    channel_info does not return all
                                    members of channel for performance
                                    reasons, but code is expecting to
                                    know at least if the current partner
                                    is member of it. (e.g. to know when
                                    to display "invited" notification)
                                    Current partner can always be assumed
                                    to be a member of channels received
                                    at init.
                                {if}
                                    {Env/currentPartner}
                                .{then}
                                    {Record/update}
                                        [0]
                                            @convertedData
                                        [1]
                                            [Thread/members]
                                                {Field/add}
                                                    {Env/currentPartner}
                                {if}
                                    {Env/currentGuest}
                                .{then}
                                    {Record/update}
                                        [0]
                                            @convertedData
                                        [1]
                                            [Thread/guestMembers]
                                                {Field/add}
                                                    {Env/currentGuest}
                            :channel
                                {Record/insert}
                                    [Record/models]
                                        Thread
                                    [Thread/model]
                                        mail.channel
                                    @convertedData
                            {Dev/comment}
                                flux specific: channels received at
                                init have to be considered pinned.
                                task-2284357
                            {if}
                                @channel
                                .{Thread/isPinned}
                                .{isFalsy}
                            .{then}
                                {Thread/pin}
                                    @channel
`;
