/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Text content that is displayed on title of the settings dialog.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            settingsTitle
        [Field/model]
            RtcCallViewer
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {Locale/text}
                Settings
`;
