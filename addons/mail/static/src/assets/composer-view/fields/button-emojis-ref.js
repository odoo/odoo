/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the ref to the html node of the emojis button.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            buttonEmojisRef
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/related]
            ComposerView/component
            ComposerViewComponent/buttonEmojis
`;
