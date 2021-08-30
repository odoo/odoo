/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            RtcOptionListComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-direction]
                column
`;
