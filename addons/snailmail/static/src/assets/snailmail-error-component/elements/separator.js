/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separator
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            hr
        [web.Element/class]
            mt-0
            mb-3
`;
