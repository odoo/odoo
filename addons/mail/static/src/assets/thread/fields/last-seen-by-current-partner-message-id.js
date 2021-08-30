/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Last seen message id of the channel by current partner.

        If there is a pending seen message id change, it is immediately applied
        on the interface to avoid a feeling of unresponsiveness. Otherwise the
        last known message id of the server is used.

        Also, it needs to be kept as an id because it's considered like a "date" and could stay
        even if corresponding message is deleted. It is basically used to know which
        messages are before or after it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastSeenByCurrentPartnerMessageId
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
        [Field/compute]
            {Dev/comment}
                Adjusts the last seen message received from the server to consider
                the following messages also as read if they are either transient
                messages or messages from the current partner.
            {if}
                @record
                .{Thread/orderedMessages}
                .{Collection/first}
                .{&}
                    @record
                    .{Thread/lastSeenByCurrentPartnerMessageId}
                .{&}
                    @record
                    .{Thread/lastSeenByCurrentPartnerMessageId}
                    .{<}
                        @record
                        .{Thread/orderedMessages}
                        .{Collection/first}
                        .{Message/id}
            .{then}
                {Dev/comment}
                    no deduction can be made if there is a gap
                @record
                .{Thread/lastSeenByCurrentPartnerMessageId}
                {break}
            :lastSeenByCurrentPartnerMessageId
                @record
                .{Thread/lastSeenByCurrentPartnerMessageId}
            {foreach}
                @record
                .{Thread/orderedMessages}
            .{as}
                message
            .{do}
                {if}
                    @message
                    .{Message/id}
                    .{<=}
                        @record
                        .{Thread/lastSeenByCurrentPartnerMessageId}
                .{then}
                    {continue}
                {if}

                    @message
                    .{Message/author}
                    .{&}
                        {Env/currentPartner}
                    .{&}
                        @message
                        .{Message/author}
                        .{=}
                            {Env/currentPartner}
                    .{|}
                        @message
                        .{Message/guestAuthor}
                        .{&}
                            {Env/currentGuest}
                        .{&}
                            @message
                            .{Message/guestAuthor}
                            .{=}
                                {Env/currentGuest}
                    .{|}
                        @message
                        .{Message/isTransient}
                .{then}
                    :lastSeenByCurrentPartnerMessageId
                        @message
                        .{Message/id}
                    {continue}
                @lastSeenByCurrentPartnerMessageId
                {break}
            @lastSeenByCurrentPartnerMessageId
`;
