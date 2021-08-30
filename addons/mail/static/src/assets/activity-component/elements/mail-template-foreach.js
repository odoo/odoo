/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mailTemplateForeach
        [Element/model]
            ActivityComponent
        [Record/models]
            Foreach
        [Foreach/collection]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/activity}
            .{Activity/mailTemplates}
        [Foreach/as]
            mailTemplate
        [Element/key]
            @field
            .{Foreach/get}
                mailTemplate
            .{Record/id}
        [Field/target]
            ActivityComponent:mailTemplate
        [ActivityComponent:mailTemplate/mailTemplate]
            @field
            .{Foreach/get}
                mailTemplate
`;
