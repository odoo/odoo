/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallViewer/toggleLayoutMenu
        [Action/params]
            record
                [type]
                    RtcCallViewer
        [Action/behavior]
            {if}
                @record
                .{RtcCallViewer/rtcLayoutMenu}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [RtcCallViewer/rtcLayoutMenu]
                            {Record/insert}
                                [Record/models]
                                    RtcLayoutMenu
            .{else}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [RtcCallViewer/rtcLayoutMenu]
                            {Record/empty}
`;
