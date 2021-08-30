/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separatorLineNewMessages
        [Element/model]
            MessageListComponent:messageContainer
        [web.Element/tag]
            hr
        [Record/models]
            MessageListComponent/separatorLine
        [web.Element/style]
            [web.scss/border-color]
                {scss/lighten}
                    {scss/$o-brand-odoo}
                    15%
`;
