/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            h4
        [web.Element/textContent]
            {Locale/text}
                Failed letter
`;
