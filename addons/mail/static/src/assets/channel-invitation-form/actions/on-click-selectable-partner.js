/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChannelInvitationForm/onClickSelectablePartner
        [Action/params]
            partner
                [type]
                    Partner
            record
                [type]
                    ChannelInvitationForm
        [Action/behavior]
            {if}
                @record
                .{ChannelInvitationForm/selectedPartners}
                .{Collection/includes}
                    @partner
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ChannelInvitationForm/selectedPartners]
                            {Field/remove}
                                @partner
            .{else}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ChannelInvitationForm/selectedPartners]
                            {Field/add}
                                @partner
`;
