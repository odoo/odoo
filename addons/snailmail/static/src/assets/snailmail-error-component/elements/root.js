/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            SnailmailErrorComponent
        [web.Element/class]
            card
            bg-white
`;
