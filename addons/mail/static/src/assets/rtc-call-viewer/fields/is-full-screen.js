/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the viewer should be displayed fullScreen.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isFullScreen
        [Field/model]
            RtcCallViewer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
