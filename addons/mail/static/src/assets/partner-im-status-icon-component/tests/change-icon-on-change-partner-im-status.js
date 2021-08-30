/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            change icon on change partner im status
        [Test/model]
            PartnerImStatusIconComponent
        [Test/assertions]
            4
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
            :partner
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Partner
                    [Partner/id]
                        7
                    [Partner/name]
                        Demo User
                    [Partner/imStatus]
                        online
            @testEnv
            .{Record/insert}
                [Record/models]
                    PartnerImStatusIconComponent
                [PartnerImStatusIconComponent/partner]
                    @partner
            {Test/assert}
                []
                    @partner
                    .{Partner/isImStatusOnline}
                []
                    partner IM status icon should have online status rendering

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{Record/update}
                    [0]
                        @partner
                    [1]
                        [Partner/imStatus]
                            offline
            {Test/assert}
                []
                    @partner
                    .{Partner/isImStatusOffline}
                []
                    partner IM status icon should have offline status rendering

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{Record/update}
                    [0]
                        @partner
                    [1]
                        [Partner/imStatus]
                            away
            {Test/assert}
                []
                    @partner
                    .{Partner/isImStatusAway}
                []
                    partner IM status icon should have away status rendering

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{Record/update}
                    [0]
                        @partner
                    [1]
                        [Partner/imStatus]
                            online
            {Test/assert}
                []
                    @partner
                    .{Partner/isImStatusOnline}
                []
                    partner IM status icon should have online status rendering in the end
`;
