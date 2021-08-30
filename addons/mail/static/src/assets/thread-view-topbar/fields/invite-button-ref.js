/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL ref of the invite button.
        Useful to provide anchor for the invite popover positioning.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            inviteButtonRef
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/related]
            ThreadViewTopbar/threadViewTopbarComponents
            Collection/first
            ThreadViewTopbarComponent/inviteButton
`;
