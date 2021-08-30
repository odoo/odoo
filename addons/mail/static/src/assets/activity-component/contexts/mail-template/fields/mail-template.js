/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mailTemplate
        [Field/model]
            ActivityComponent:mailTemplate
        [Field/type]
            one
        [Field/target]
            MailTemplate
        [Field/isRequired]
            true
`;
