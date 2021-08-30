/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separatorDateLineStart
        [Element/model]
            MessageListComponent:messageContainer
        [web.Element/tag]
            hr
        [Record/models]
            MessageListComponent/separatorLine
`;
