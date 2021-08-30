/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        global JS generated ID for this component. Useful to provide a
        custom class to autocomplete input, so that click in an autocomplete
        item is not considered as a click away from messaging menu in mobile.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            MessagingMenuComponent
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            {UnderscoreJS/uniqueId}
                o-MessagingMenuComponent-
`;
