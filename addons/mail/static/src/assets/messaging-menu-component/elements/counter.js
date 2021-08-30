/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            counter
        [Element/model]
            MessagingMenuComponent
        [web.Element/tag]
            span
        [web.Element/class]
            badge
            badge-pill
        [Element/isPresent]
            {Messaging/isInitialized}
            .{&}
                {MessagingMenu/counter}
                .{>}
                    0
        [web.Element/textContent]
            {MessagingMenu/counter}
        [web.Element/style]
            [web.scss/position]
                relative
            [web.scss/transform]
                {web.scss/translate}
                    -5px
                    -5px
            [web.scss/margin-right]
                -10px
                {Dev/comment}
                    "cancel" right padding of systray items
            [web.scss/background-color]
                {scss/$o-enterprise-primary-color}
`;
