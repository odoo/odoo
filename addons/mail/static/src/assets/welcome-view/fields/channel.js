/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the channel to redirect to once the user clicks on the
        'joinButton'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channel
        [Field/model]
            WelcomeView
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
