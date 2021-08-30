/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mobileNavbar
        [Element/model]
            DiscussComponent
        [Field/target]
            MobileMessagingNavbarComponent
        [Element/isPresent]
            {Discuss/mobileMessagingNavbarView}
        [MobileMessagingNavbarComponent/mobileMessagingNavbarView]
            {Discuss/mobileMessagingNavbarView}
        [web.Element/style]
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
`;
