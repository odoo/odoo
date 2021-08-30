/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            grouped notifications by document model
        [Test/feature]
            sms
        [Test/model]
            NotificationListComponent
        [Test/assertions]
            12
        [Test/scenario]
            {Dev/comment}
                If all failures linked to a document model refers to different documents,
                a single notification should group all failures that are linked to this
                document model.
            :bus
                {Record/insert}
                    [Record/models]
                        Bus
            {Bus/on}
                [0]
                    @bus
                [1]
                    do-action
                [2]
                    null
                [3]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            payload
                        [Function/out]
                            {Test/step}
                                do_action
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        action
                                    .{Dict/get}
                                        name
                                    .{=}
                                        SMS Failures
                                []
                                    action should have 'SMS Failures' as name
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        action
                                    .{Dict/get}
                                        type
                                    .{=}
                                        ir.actions.act_window
                                []
                                    action should have the type act_window
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        action
                                    .{Dict/get}
                                        view_mode
                                    .{=}
                                        kanban,list,form
                                []
                                    action should have 'kanban,list,form' as view_mode
                            {Test/assert}
                                []
                                    {JSON/stringify}
                                        @payload
                                        .{Dict/get}
                                            action
                                        .{Dict/get}
                                            views
                                    .{=}
                                        {JSON/stringify}
                                            {Record/insert}
                                                [Record/models]
                                                    Collection
                                                [0]
                                                    [0]
                                                        false
                                                    [1]
                                                        kanban
                                                [1]
                                                    [0]
                                                        false
                                                    [1]
                                                        list
                                                [2]
                                                    [0]
                                                        false
                                                    [1]
                                                        form
                                []
                                    action should have correct views
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        action
                                    .{Dict/get}
                                        target
                                    .{=}
                                        current
                                []
                                    action should have 'current' as target
                            {Test/assert}
                                []
                                    @payload
                                    .{Dict/get}
                                        action
                                    .{Dict/get}
                                        res_model
                                    .{=}
                                        res.partner
                                []
                                    action should have the group model as res_model
                            {Test/assert}
                                []
                                    {JSON/stringify}
                                        @payload
                                        .{Dict/get}
                                            action
                                        .{Dict/get}
                                            domain
                                    .{=}
                                        {JSON/stringify}
                                            message_has_sms_error
                                            .{=}
                                                true
                                []
                                    action should have 'message_has_sms_error' as domain
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [bus]
                            @bus
            @testEnv
            .{Record/insert}
                []
                    {Dev/comment}
                        first message that is expected to have a failure
                    [Record/models]
                        mail.message
                    [mail.message/id]
                        11
                        {Dev/comment}
                            random unique id, will be used to link failure to message
                    [mail.message/message_type]
                        sms
                        {Dev/comment}
                            message must be sms (goal of the test)
                    [mail.message/model]
                        res.partner
                        {Dev/comment}
                            same model as second message (and not 'mail.channel')
                    [mail.message/res_id]
                        31
                        {Dev/comment}
                            different res_id from second message
                    [mail.message/res_model_name]
                        Partner
                        {Dev/comment}
                            random related model name
                []
                    {Dev/comment}
                        second message that is expected to have a failure
                    [Record/models]
                        mail.message
                    [mail.message/id]
                        12
                        {Dev/comment}
                            random unique id, will be used to link failure to message
                    [mail.message/message_type]
                        sms
                        {Dev/comment}
                            message must be sms (goal of the test)
                    [mail.message/model]
                        res.partner
                        {Dev/comment}
                            same model as first message (and not 'mail.channel')
                    [mail.message/res_id]
                        32
                        {Dev/comment}
                            different res_id from first message
                    [mail.message/res_model_name]
                        Partner
                        {Dev/comment}
                            same related model name for consistency
                []
                    {Dev/comment}
                        first failure that is expected to be used in the test
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        11
                        {Dev/comment}
                            id of the related first message
                    [mail.notification/notification_status]
                        exception
                        {Dev/comment}
                            necessary value to have a failure
                    [mail.notification/notification_type]
                        sms
                        {Dev/comment}
                            expected failure type for sms message
                []
                    {Dev/comment}
                        second failure that is expected to be used in the test
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        12
                        {Dev/comment}
                            id of the related second message
                    [mail.notification/notification_status]
                        exception
                        {Dev/comment}
                            necessary value to have a failure
                    [mail.notification/notification_type]
                        sms
                        {Dev/comment}
                            expected failure type for sms message
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    NotificationListComponent
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have 1 notification group
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/counter}
                []
                    should have 1 group counter
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            NotificationListComponent
                    .{Collection/first}
                    .{NotificationListComponent/group}
                    .{Collection/first}
                    .{NotificationGroupComponent/counter}
                    .{web.Element/textContent}
                    .{=}
                        (2)
                []
                    should have 2 notifications in the group

            @testEnv
            .{UI/click}
                @testEnv
                .{Record/all}
                    [Record/models]
                        NotificationListComponent
                .{Collection/first}
                .{NotificationListComponent/group}
                .{Collection/first}
            {Test/verifySteps}
                []
                    do_action
                []
                    should do an action to display the related records
`;
