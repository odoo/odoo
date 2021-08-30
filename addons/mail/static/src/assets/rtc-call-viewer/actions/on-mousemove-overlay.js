/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallViewer/onMousemoveOverlay
        [Action/params]
            ev
                [type]
                    MouseEvent
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
            {Event/markAsHandled}
                [0]
                    @ev
                [1]
                    RtcCallViewer/onMousemoveOverlay
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcCallViewer/showOverlay]
                        true
            {Browser/clearTimeout}
                @record
                .{RtcCallViewer/showOverlayTimeout}
`;
