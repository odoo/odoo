/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        This component abstracts chatter component to its parent, so that it can be
        mounted and receive chatter data even when a chatter component cannot be
        created. Indeed, in order to create a chatter component, we must create
        a chatter record, the latter requiring messaging to be initialized. The view
        may attempt to create a chatter before messaging has been initialized, so
        this component delays the mounting of chatter until it becomes initialized.
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChatterContainerComponent
        [Model/fields]
            _chatterId
            chatter
            hasActivities
            hasExternalBorder
            hasFollowers
            hasMessageList
            hasMessageListScrollAdjust
            hasParentReloadOnAttachmentsChanged
            hasTopbarCloseButton
            isAttachmentBoxVisibleInitially
            threadId
            threadModel
        [Model/template]
            root
                chatterPart
                noChatter
                    noChatterIcon
                    noChatterLabel
        [Model/actions]
            ChatterContainerComponent/_convertPropsToChatterFields
            ChatterContainerComponent/_insertFromProps
            ChatterContainerComponent/getChatterNextTemporaryId
        [Model/lifecycles]
            onUpdate
            onDestroy
            onWillUpdateProps
`;
