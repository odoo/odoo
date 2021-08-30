/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallViewer/onLayoutSettingsDialogClosed
        [Action/params]
            ev
                [type]
                    CustomEvent
            record
                [type]
                    RtcCallViewer
        [Action/behavior]
            {RtcCallViewer/toggleLayoutMenu}
                @record
`;
