/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the name the guest had when landing on the welcome view.

        Useful to determine whether the name has changed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            originalGuestName
        [Field/model]
            WelcomeView
        [Field/type]
            attr
        [Field/target]
            String`;
