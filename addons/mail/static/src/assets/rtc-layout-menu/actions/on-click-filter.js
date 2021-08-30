/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcLayoutMenu/onClickFilter
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    RtcLayoutMenu
        [Action/behavior]
            {web.Event/preventDefault}
                @ev
            {switch}
                @ev
                .{web.Event/target}
                .{web.Element/value}
            .{case}
                [all]
                    {Record/update}
                        [0]
                            @record
                            .{RtcLayoutMenu/callViewer}
                        [1]
                            [CallViewer/filterVideoGrid]
                                false
                [video]
                    {Record/update}
                        [0]
                            @record
                            .{RtcLayoutMenu/callViewer}
                        [1]
                            [CallViewer/filterVideoGrid]
                                true
                    {if}
                        {Env/focusedRtcSession}
                        .{&}
                            {Env/focusedRtcSession}
                            .{RtcSession/videoStream}
                            .{isFalsy}
                    .{then}
                        {Record/update}
                            [0]
                                @env
                            [1]
                                [Env/focusedRtcSession]
                                    {Record/empty}
`;
