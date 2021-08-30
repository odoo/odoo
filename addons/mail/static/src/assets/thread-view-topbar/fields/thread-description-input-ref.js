/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL ref of the thread description input of this top bar.
        Useful to focus it, or to know when a click is done outside of it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadDescriptionInputRef
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            one
        [Field/target]
            Element
        [Field/compute]
            @record
            .{ThreadViewTopbar/threadViewTopbarComponents}
            .{Collection/first}
            .{ThreadViewTopbarComponent/threadDescriptionInput}
`;
