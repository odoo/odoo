/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        All threads that this message is linked to. This field is read-only.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threads
        [Field/model]
            Message
        [Field/type]
            many
        [Field/target]
            Thread
        [Field/inverse]
            Thread/messages
        [Field/compute]
            :threads
                {Record/insert}
                    [Record/models]
                        Collection
            {if}
                @record
                .{Message/isHistory}
            .{then}
                {Collection/push}
                    @threads
                    {Env/history}
            {if}
                @record
                .{Message/isNeedaction}
            .{then}
                {Collection/push}
                    @threads
                    {Env/inbox}
            {if}
                @record
                .{Message/isStarred}
            .{then}
                {Collection/push}
                    @threads
                    {Env/starred}
            {if}
                @record
                .{Message/originThread}
            .{then}
                {Collection/push}
                    @threads
                    @record
                    .{Message/originThread}
            @threads
`;
