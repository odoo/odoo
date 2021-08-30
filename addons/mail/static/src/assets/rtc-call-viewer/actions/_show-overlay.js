/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Shows the overlay (buttons) for a set a mount of time.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallViewer/_showOverlay
        [Action/params]
            record
                [type]
                    RtcCallViewer
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcCallViewer/showOverlay]
                        true
            {Browser/clearTimeout}
                @record
                .{RtcCallViewer/showOverlayTimeout}
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcCallViewer/showOverlayTimeout]
                        {Browser/setTimeout}
                            [0]
                                {RtcCallViewer/_onShowOverlayTimeout}
                                    @record
                            [1]
                                3000
`;
