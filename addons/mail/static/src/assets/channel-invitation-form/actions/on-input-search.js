/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChannelInvitationForm/onInputSearch
        [Action/params]
            ev
                [type]
                    web.InputEvent
            record
                [type]
                    ChannelInvitationForm
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ChannelInvitationForm/searchTerm]
                        @ev
                        .{web.Event/target}
                        .{web.Element/value}
            {ChannelInvitationForm/searchPartnersToInvite}
                @record
`;
