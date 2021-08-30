/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        URL to access to the conversation.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            url
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            :baseHref
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    session
                .{Dict/get}
                    url
                .{Function/call}
                    /web
            {if}
                @record
                .{Thread/model}
                .{=}
                    mail.channel
            .{then}
                @baseHref
                .{+}
                #action=mail.action_discuss&active_id=
                .{+}
                    @record
                    .{Thread/model}
                .{+}
                    _
                +{+}
                    @record
                    .{Thread/id}
            .{else}
                @baseHref
                .{+}
                    #model=
                .{+}
                    @record
                    .{Thread/model}
                .{+}
                    &id=
                .{+}
                    @record
                    .{Thread/id}
`;
