/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonContent
        [Element/model]
            RtcActivityNoticeComponent
        [web.Element/class]
            d-flex
            align-items-center
        [web.Element/style]
            [web.scss/max-width]
                150px
`;
