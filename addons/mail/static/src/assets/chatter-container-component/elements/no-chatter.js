/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            noChatter
        [Element/model]
            ChatterContainerComponent
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
`;
