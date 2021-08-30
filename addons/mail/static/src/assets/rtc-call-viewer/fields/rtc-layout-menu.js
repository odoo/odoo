/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The model for the menu to control the layout of the viewer.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcLayoutMenu
        [Field/model]
            RtcCallViewer
        [Field/type]
            one
        [Field/target]
            RtcLayoutMenu
        [Field/isCausal]
            true
        [Field/inverse]
            RtcLayoutMenu/callViewer
`;
