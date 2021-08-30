/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            newMessageButtonMobile
        [Element/model]
            MessagingMenuComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-secondary
        [Element/isPresent]
            {Device/isMobile}
        [Element/onClick]
            {MessagingMenu/toggleMobileNewMessage}
        [web.Element/type]
            button
        [web.Element/textContent]
            {Locale/text}
                New message
        [web.Element/style]
            [web.scss/grid-area]
                top
            [web.scss/justify-self]
                start
`;
