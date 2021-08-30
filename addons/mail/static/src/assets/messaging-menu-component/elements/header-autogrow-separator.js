/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headerAutogrowSeparator
        [Element/model]
            MessagingMenuComponent
        [Record/models]
            AutogrowComponent
`;
