/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the extra 'Partner' (on top of existing followers)
        that will receive the message being composed by 'this', and that will
        also be added as follower of 'this.activeThread'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            recipients
        [Field/model]
            Composer
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/compute]
            :recipients
                @record
                .{Composer/mentionedPartners}
            {if}
                @record
                .{Composer/activeThread}
                .{&}
                    @record
                    .{Composer/isLog}
                    .{isFalsy}
            .{then}
                {foreach}
                    @record
                    .{Composer/activeThread}
                    .{Thread/suggestedRecipientInfoList}
                .{as}
                    recipient
                .{do}
                    {if}
                        @recipient
                        .{SuggestedRecipientInfo/partner}
                        .{&}
                            @recipient
                            .{SuggestedRecipientInfo/isSelected}
                    .{then}
                        {Collection/push}
                            [0]
                                @recipients
                            [1]
                                @recipient
                                .{SuggestedRecipientInfo/partner}
            @recipients
`;
