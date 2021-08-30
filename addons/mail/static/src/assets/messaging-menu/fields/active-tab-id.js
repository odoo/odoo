/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Tab selected in the messaging menu.
        Either 'all', 'chat' or 'channel'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activeTabId
        [Field/model]
            MessagingMenu
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            all
`;
