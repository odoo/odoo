/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mailTemplates
        [Field/model]
            Activity
        [Field/type]
            many
        [Field/target]
            MailTemplate
        [Field/inverse]
            MailTemplate/activities
`;
