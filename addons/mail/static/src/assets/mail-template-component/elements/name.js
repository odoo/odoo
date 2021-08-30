/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            MailTemplateComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{MailTemplateComponent/mailTemplate}
        [web.Element/textContent]
            @record
            .{MailTemplateComponent/mailTemplate}
            .{MailTemplate/name}
        [web.Element/style]
            [web.scss/margin-inline-start]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
