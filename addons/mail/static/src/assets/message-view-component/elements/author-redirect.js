/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            authorRedirect
        [Element/model]
            MessageViewComponent
        [web.Element/style]
            [web.scss/cursor]
                pointer
`;
