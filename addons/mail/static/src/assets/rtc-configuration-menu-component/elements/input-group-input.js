/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inputGroupInput
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            input
        [web.Element/type]
            range
        [web.Element/style]
            [web.scss/flex-grow]
                2
`;
