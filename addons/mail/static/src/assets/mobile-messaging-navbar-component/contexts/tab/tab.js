/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            tab
        [Context/model]
            MobileMessagingNavbarComponent
        [Model/fields]
            tab
        [Model/template]
            tabForeach
                tab
                    tabIcon
                    tabLabel
`;
