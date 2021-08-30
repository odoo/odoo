/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            creditBuyLabel
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            Buy credits
`;
