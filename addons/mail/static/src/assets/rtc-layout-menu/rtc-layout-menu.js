/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcLayoutMenu
        [Model/fields]
            callViewer
            component
        [Model/id]
            RtcLayoutMenu/callViewer
        [Model/actions]
            RtcLayoutMenu/onClickFilter
            RtcLayoutMenu/onClickLayout
`;
