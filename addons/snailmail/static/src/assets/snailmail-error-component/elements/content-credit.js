/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            contentCredit
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            p
        [web.Element/class]
            mx-3
            mb-3
        [web.Element/textContent]
            {Locale/text}
                The letter could not be sent due to insufficient credits on your IAP account.
`;
