/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttons
        [Element/model]
            SnailmailErrorComponent
        [web.Element/class]
            mx-3
            mb-3
`;
