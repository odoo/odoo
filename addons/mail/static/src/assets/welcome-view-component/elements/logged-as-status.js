/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loggedAsStatus
        [Element/model]
            WelcomeViewComponent
        [Element/isPresent]
            {Env/currentUser}
        [web.Element/tag]
            p
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    Logged as %s
                [1]
                    {Env/currentUser}
                    .{User/nameOrDisplayName}
        [web.Element/style]
            [web.scss/font-size]
                {scss/$font-size-lg}
`;
