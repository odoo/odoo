/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonIcon
        [Element/model]
            RtcInvitationCardComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-lg
        [web.Element/style]
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    3
`;
