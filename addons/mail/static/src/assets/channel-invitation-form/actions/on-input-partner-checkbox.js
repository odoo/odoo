/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChannelInvitationForm/onInputPartnerCheckbox
        [Action/params]
            ev
                [type]
                    web.InputEvent
            partner
                [type]
                    Partner
            record
                [type]
                    ChannelInvitationForm
        [Action/behavior]
            {if}
                @ev
                .{web.Event/target}
                .{web.Element/isChecked}
                .{isFalsy}
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
