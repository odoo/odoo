/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether there was at least one programmatic scroll since the
        last scroll event was handled (which is particularly async due to
        throttled behavior).
        Useful to avoid loading more messages or to incorrectly disabling the
        auto-scroll feature when the scroll was not made by the user.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isLastScrollProgrammatic
        [Field/model]
            MessageListView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
