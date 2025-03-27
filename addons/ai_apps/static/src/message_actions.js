import { patch } from "@web/core/utils/patch";

import { user } from '@web/core/user';
import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry, messageActionsInternal } from "@mail/core/common/message_actions";

messageActionsRegistry
    .add("insertToComposer", {
        condition: (component) => (
            component.props.thread.channel_type === "ai_composer" &&  // only show button in ai_composer chat
            component.message.Model.insertButtonCaller && (  // after a reload both parts of the below conditions are undefined and but we don't want to button to appear
                component.message.Model.insertButtonCaller === component.env.chatCaller ||  // only show button when the modal that called the AI is mounted
                component.env.isSmall
            ) &&
            component.message.author.userId !== user.userId  // don't show the buttons for the user's messages
        ),
        title: () => _t("Use this"),
        onClick: (component) => {
            const fragment = document.createDocumentFragment();
            const content_root = document.createElement('span');
            content_root.setAttribute('InsertorId', 'AIInsertion');
            content_root.innerHTML = component.props.message.body.replace(/^<p>(.*?)<\/p>$/, '$1');
            fragment.appendChild(content_root);
            if (component.env.isSmall) {
                component.props.insertToEditor(fragment);
                component.props.thread.closeChatWindow();
            } else {
                component.env.specialActions['insert'](fragment);
            }
        },
        sequence: 0,
    })
    .add("copy-message", {
        condition: (component) => component.props.thread.channel_type === "ai_composer",
        icon: "fa fa-copy",
        title: _t("Copy to Clipboard"),
        onClick: (component) => component.message.copyMessageText(),
        sequence: 1,
    });;
    
patch(messageActionsInternal, {
    condition(component, id, action) {
        const requiredActions = ['insertToComposer', 'copy-message'];
        if (
            component.props.thread.channel_type === 'ai_composer' && 
            !requiredActions.includes(id)
        ) {
            return false
        }
        return super.condition(component, id, action);
    }
})
