/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            rightSection
        [Element/model]
            ChatterTopbarComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                1
                0
                auto
            [web.scss/justify-content]
                flex-end
`;
