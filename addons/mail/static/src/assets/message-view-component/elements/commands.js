/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commands
        [Element/model]
            MessageViewComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
`;
