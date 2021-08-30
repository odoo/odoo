/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            creditsBuyContainer
        [Element/model]
            SnailmailErrorComponent
        [Element/isPresent]
            {Env/snailmailCreditsUrl}
        [web.Element/class]
            text-right
            mx-3
            mb-3
`;
