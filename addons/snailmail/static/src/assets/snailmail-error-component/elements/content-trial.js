/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            contentTrial
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            p
        [web.Element/class]
            mx-3
            mb-3
        [web.Element/textContent]
            {Locale/text}
                You need credits on your IAP account to send a letter.
`;
