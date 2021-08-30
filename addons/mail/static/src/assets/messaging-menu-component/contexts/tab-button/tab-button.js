/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            tabButton
        [Context/model]
            MessagingMenuComponent
        [Model/fields]
            tabId
        [Model/template]
            tabButtonForeach
                tabButton
`;
