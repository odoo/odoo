/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mailTemplate
        [Element/model]
            ActivityComponent:mailTemplate
        [Field/target]
            MailTemplateComponent
        [MailTemplateComponent/activity]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
        [MailTemplateComponent/mailTemplate]
            @record
            .{ActivityComponent:mailTemplate/mailTemplate}
`;
