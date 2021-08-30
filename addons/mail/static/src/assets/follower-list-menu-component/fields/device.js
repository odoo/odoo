/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            device
        [Field/model]
            FollowerListMenuComponent
        [Field/type]
            one
        [Field/target]
            Device
        [Field/default]
            {Env/device}
        [Field/observe]
            {Record/insert}
                [Record/models]
                    FieldObserver
                [FieldObserver/event]
                    click
                [FieldObserver/callback]
                    {Dev/comment}
                        since dropdown is conditionally shown based on state,
                        dropdownRef can be null
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            ev
                        [Function/out]
                            {if}
                                @record
                                .{FollowerListMenuComponent/followers}
                                .{&}
                                    @record
                                    .{FollowerListMenuComponent/followers}
                                    .{web.Element/contains}
                                        @ev
                                        .{web.Event/target}
                                    .{isFalsy}
                            .{then}
                                {FollowerListMenuComponent/_hide}
                                    @record
                                    @ev
`;
