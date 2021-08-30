/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            optionLabel
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            label
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/flex-wrap]
                wrap
            [web.scss/max-width]
                100%
            [web.scss/cursor]
                pointer
`;
