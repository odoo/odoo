/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trialBuyLabel
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                Buy credits
`;
