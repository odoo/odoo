/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            tabId
        [Field/model]
            MessagingMenuComponent:tabButton
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isRequired]
            true
`;
