/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallViewer/_onShowOverlayTimeout
        [Action/params]
            record
                [type]
                    RtcCallViewer
        [Action/behavior]
            {if}
                {Record/exists}
                    @record
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcCallViewer/showOverlay]
                        false
`;
