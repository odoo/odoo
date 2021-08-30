/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the welcome view linked to this discuss public view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            welcomeView
        [Field/model]
            DiscussPublicView
        [Field/type]
            one
        [Field/target]
            WelcomeView
        [Field/isCausal]
            true
        [Field/inverse]
            WelcomeView/discussPublicView
`;
