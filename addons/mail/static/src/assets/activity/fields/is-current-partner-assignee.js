/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isCurrentPartnerAssignee
        [Field/model]
            Activity
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {if}
                @record
                .{Activity/assignee}
                .{isFalsy}
            .{then}
                false
                {break}
            {if}
                {Env/currentPartner}
                .{isFalsy}
            .{then}
                false
                {break}
            {if}
                @record
                .{Activity/assignee}
                .{User/partner}
                .{isFalsy}
            .{then}
                false
                {break}
            @record
            .{Activity/assignee}
            .{User/partner}
            .{=}
                {Env/currentPartner}
`;
