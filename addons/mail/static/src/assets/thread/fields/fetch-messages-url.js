/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            fetchMessagesUrl
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {switch}
                @record
            .{case}
                {entry}
                    [key]
                        {Env/inbox}
                    [value]
                        /mail/inbox/messages
                        {break}
                {entry}
                    [key]
                        {Env/history}
                    [value]
                        /mail/history/messages
                        {break}
                {entry}
                    [key]
                        {Env/starred}
                    [value]
                        /mail/starred/messages
                        {break}
            {if}
                @record
                .{Thread/model}
                .{=}
                    mail.channel
            .{then}
                /mail/channel/messages
            .{else}
                /mail/thread/messages
`;
