/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            showOnlyVideoInput
        [Element/model]
            RtcLayoutMenuComponent
        [Record/models]
            RtcLayoutMenuComponent/input
        [web.Element/name]
            filter
        [web.Element/value]
            video
        [Element/onClick]
            {RtcLayoutMenu/onClickFilter}
                [0]
                    @record
                    .{RtcLayoutMenuComponent/layoutMenu}
                [1]
                    @ev
        [web.Element/isChecked]
            @record
            .{RtcLayoutMenuComponent/layoutMenu}
            .{RtcLayoutMenu/callViewer}
            .{RtcCallViewer/filterVideoGrid}
`;
