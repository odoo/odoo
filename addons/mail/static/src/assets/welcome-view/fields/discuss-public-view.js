/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States discuss public view on which this welcome view is displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussPublicView
        [Field/model]
            WelcomeView
        [Field/type]
            one
        [Field/target]
            DiscussPublicView
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            DiscussPublicView/welcomeView
`;
