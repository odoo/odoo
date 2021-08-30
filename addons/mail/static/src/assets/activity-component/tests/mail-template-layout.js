/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            mail template layout
        [Test/model]
            ActivityComponent
        [Test/assertions]
            8
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        res.partner
                    [res.partner/activity_ids]
                        12
                    [res.partner/id]
                        100
                []
                    [Record/models]
                        mail.template
                    [mail.template/id]
                        1
                    [mail.template/name]
                        Dummy mail template
                []
                    [Record/models]
                        mail.activity
                    [mail.activity/activity_type_id]
                        1
                    [mail.activity/id]
                        12
                    [mail.activity/mail_template_ids]
                        1
                    [mail.activity/res_id]
                        100
                    [mail.activity/res_model]
                        res.partner
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have activity component
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/length}
                    .{ActivityComponent/sidebar}
                []
                    should have activity sidebar
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/mailTemplates}
                []
                    should have activity mail templates
            {Test/assert}
                []
                    @activity
                    .{Activity/activityComponents}
                    .{Collection/first}
                    .{ActivityComponent/mailTemplate}
                []
                    should have activity mail template
            {Test/assert}
                []
                    @activity
                    .{Activity/mailTemplates}
                    .{Collection/first}
                    .{MailTemplate/mailTemplateComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have activity mail template name
            {Test/assert}
                []
                    @activity
                    .{Activity/mailTemplates}
                    .{Collection/first}
                    .{MailTemplate/mailTemplateComponents}
                    .{Collection/first}
                    .{MailTemplateComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Dummy mail template
                []
                    should have activity mail template name
            {Test/assert}
                []
                    @activity
                    .{Activity/mailTemplates}
                    .{Collection/first}
                    .{MailTemplate/mailTemplateComponents}
                    .{Collection/first}
                    .{MailTemplateComponent/preview}
                []
                    should have activity mail template name preview button
            {Test/assert}
                []
                    @activity
                    .{Activity/mailTemplates}
                    .{Collection/first}
                    .{MailTemplate/mailTemplateComponents}
                    .{Collection/first}
                    .{MailTemplateComponent/send}
                []
                    should have activity mail template name send button
`;
