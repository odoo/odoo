/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the default display mode of this channel. Should contain
        either no value (to display the chat), or 'video_full_screen' to
        start a call in full screen.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            defaultDisplayMode
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
`;
