/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatarContainer
        [Element/model]
            VisitorBannerComponent
        [web.Element/style]
            [web.scss/height]
                {scss/$o-mail-thread-avatar-size}
            [web.scss/width]
                {scss/$o-mail-thread-avatar-size}
            [web.scss/margin-left]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/position]
                relative
`;
