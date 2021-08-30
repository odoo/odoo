/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the last change (since the last render) was
        programmatic. Useful to avoid restoring the state when its change was
        from a user action, in particular to prevent the cursor from jumping
        to its previous position after the user clicked on the textarea while
        it didn't have the focus anymore.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isLastStateChangeProgrammatic
        [Field/model]
            Composer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
