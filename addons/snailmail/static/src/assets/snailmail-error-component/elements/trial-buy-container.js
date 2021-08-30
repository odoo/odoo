/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trialBuyContainer
        [Element/model]
            SnailmailErrorComponent
        [Element/isPresent]
            {Env/snailmailCreditsUrlTrial}
        [web.Element/class]
            text-right
            mx-3
            mb-3
`;
