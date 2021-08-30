/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic rendering of tracking value (float type)
        [Test/model]
            TrackingValue
        [Test/assertions]
            8
        [Test/behavior]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    mail.test.track.all
                [mail.test.track.all/float_field]
                    12.30
                [mail.test.track.all/id]
                    1
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
                        mail.test.track.all
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
                        input[name=float_field]
                [1]
                    45.67
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
                []
                    should display a tracking value
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValueFieldName}
                []
                    should display the name of the tracked field
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValueFieldName}
                    .{web.Element/textContent}
                    .{=}
                        Float:
                []
                    should display the correct tracked field name (Float)
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValueOldValue}
                []
                    should display the old value
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValueOldValue}
                    .{web.Element/textContent}
                    .{=}
                        12.30
                []
                    should display the correct old value (12.30)
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValueSeparator}
                []
                    should display the separator
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValueNewValue}
                []
                    should display the new value
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            MessageViewComponent
                    .{Collection/first}
                    .{MessageViewComponent/trackingValueNewValue}
                    .{web.Element/textContent}
                    .{=}
                        45.67
                []
                    should display the correct new value (45.67)
`;
