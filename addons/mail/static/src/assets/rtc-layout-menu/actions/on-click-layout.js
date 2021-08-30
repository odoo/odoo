/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcLayoutMenu/onClickLayout
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
            {Record/update}
                [0]
                    {Env/userSetting}
                [1]
                    [UserSetting/rtcLayout]
                        @ev
                        .{web.Event/target}
                        .{web.Element/value}
            {Component/trigger}
                [0]
                    @record
                    .{RtcLayoutMenu/component}
                [1]
                    dialog-closed
`;
