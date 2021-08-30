/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnerAvatarContainer
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [web.Element/class]
            flex-shrink-0
            position-relative
        [web.Element/style]
            [web.scss/width]
                32
                px
            [web.scss/height]
                32
                px
`;
