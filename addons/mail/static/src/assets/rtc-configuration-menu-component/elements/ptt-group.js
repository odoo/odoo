/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttGroup
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            span
        [web.Element/style]
            [web.scss/display]
                flex
`;
