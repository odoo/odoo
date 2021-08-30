/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mailTemplate
        [Field/model]
            MailTemplateComponent
        [Field/type]
            one
        [Field/target]
            MailTemplate
        [Field/isRequired]
            true
`;
