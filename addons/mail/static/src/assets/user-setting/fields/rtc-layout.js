/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        layout of the rtc session display chosen by the user
        possible values: tiled, spotlight, sidebar
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcLayout
        [Field/model]
            UserSetting
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            tiled
`;
