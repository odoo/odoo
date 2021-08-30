/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            text
        [Element/model]
            MailTemplateComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                or
        [web.Element/style]
            [web.scss/color]
                {scss/gray}
                    500
            [web.scss/font-style]
                italic
`;
