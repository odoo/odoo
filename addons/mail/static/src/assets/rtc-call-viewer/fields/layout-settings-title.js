/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Text content that is displayed on title of the layout settings dialog.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            layoutSettingsTitle
        [Field/model]
            RtcCallViewer
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {Locale/text}
                Change Layout
`;
