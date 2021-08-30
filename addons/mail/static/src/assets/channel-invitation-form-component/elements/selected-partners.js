/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectedPartners
        [Element/model]
            ChannelInvitationFormComponent
        [web.Element/class]
            overflow-auto
        [web.Element/style]
            [web.scss/max-height]
                100
                px
`;
