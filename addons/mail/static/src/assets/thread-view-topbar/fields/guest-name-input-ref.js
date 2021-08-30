/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL ref of the "guest name" input of this top bar.
        Useful to focus it, or to know when a click is done outside of it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            guestNameInputRef
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/compute]
            @record
            .{ThreadViewTopbar/component}
            .{ThreadViewTopbarComponent/guestNameInput}
`;
