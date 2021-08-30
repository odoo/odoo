/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            coreAutogrowSeparator
        [Element/model]
            NotificationGroupComponent
        [web.Element/tag]
            span
        [Record/models]
            AutogrowComponent
`;
