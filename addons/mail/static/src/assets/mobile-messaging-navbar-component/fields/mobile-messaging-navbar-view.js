/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mobileMessagingNavbarView
        [Field/model]
            MobileMessagingNavbarComponent
        [Field/type]
            one
        [Field/target]
            MobileMessagingNavbarView
        [Field/isRequired]
            true
`;
