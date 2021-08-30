/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            rendering of tracked field of type integer: from 0 to non-0
        [Test/model]
            TrackingValue
        [Test/assertions]
            1
        [Test/behavior]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    mail.test.track.all
                [mail.test.track.all/id]
                    1
                [mail.test.track.all/integer_field]
                    0
            :form
                @testEnv
                .{Record/insert}
                    [Record/models]
                        View
                    [View/arch]
                        <form>
                            <sheet>
                                <field name="boolean_field"/>
                                <field name="char_field"/>
                                <field name="date_field"/>
                                <field name="datetime_field"/>
                                <field name="float_field"/>
                                <field name="integer_field"/>
                                <field name="monetary_field"/>
                                <field name="many2one_field_id"/>
                                <field name="selection_field"/>
                                <field name="text_field"/>
                            </sheet>
                            <div class="oe_chatter">
                                <field name="message_ids"/>
                            </div>
                        </form>
                    [View/archs]
                        [mail.message,false,list]
                            <tree/>
                    [View/model]
                        mail.testtrack.all
                    [View/View]
                        FormView
                    [View/viewOptions]
                        [mode]
                            edit
                    [View/res_id]
                        1
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Fields/editInput}
                [0]
                    @form
                    .{jQuery.Element/selector}
                        input[name=integer_field]
                [1]
                    1
            @testEnv
            .{Form/clickSave}
                @form
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValue}
                    .{web.Element/textContent}
                    .{=}
                        Integer:01
                []
                    should display the correct content of tracked field of type integer: from 0 to non-0 (Integer: 0 -> 1)
`;
