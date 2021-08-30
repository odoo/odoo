/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            replyingToMessageComposer
        [Element/model]
            DiscussComponent
`;
