import { patch } from "@web/core/utils/patch";

import { user } from '@web/core/user';
import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry, messageActionsInternal } from "@mail/core/common/message_actions";

messageActionsRegistry
    .add("insertToComposer", {
        condition: (component) => (
            component.props.thread.channel_type === "ai_composer" &&
            component.store.aiInsertButtonTarget && (  // after a reload both parts of the below conditions are undefined and but we don't want to button to appear
                component.store.aiInsertButtonTarget === component.props.thread.aiChatSource ||
                component.env.isSmall
            ) &&
            component.message.author.userId !== user.userId
        ),
        title: () => _t("Use this"),
        onClick: (component) => {
            const fragment = document.createDocumentFragment();
            const content_root = document.createElement('span');
            content_root.setAttribute('InsertorId', 'AIInsertion');
            content_root.innerHTML = component.props.message.body.replace(/^<p>(.*?)<\/p>$/, '$1');
            fragment.appendChild(content_root);
            component.props.thread.aiSpecialActions['insert'](fragment);
            if (component.env.isSmall) {
                component.props.thread.closeChatWindow();
            }
        },
        sequence: 10,
    })
    .add("copy-message", {
        condition: (component) => component.props.thread.channel_type === "ai_composer",
        icon: "fa fa-copy",
        title: _t("Copy to Clipboard"),
        onClick: (component) => component.message.copyMessageText(),
        sequence: 30,
    })
    .add("send-message-direct", {
        condition: (component) => (
            !!component.props.thread.aiSpecialActions?.['sendMessage'] &&
            component.message.author.userId !== user.userId  // don't show the buttons for the user's messages
        ),
        title: _t("Send as Message"),
        onClick: (component) => {
            component.props.thread.aiSpecialActions['sendMessage'](component.props.message.body);
        },
        sequence: 10,
    })
    .add("log-note-direct", {
        condition: (component) => (
            !!component.props.thread.aiSpecialActions?.['logNote'] &&
            component.message.author.userId !== user.userId  // don't show the buttons for the user's messages
        ),
        title: _t("Log as Note"),
        onClick: (component) => component.props.thread.aiSpecialActions['logNote'](component.props.message.body),
        sequence: 20,
    });
    
patch(messageActionsInternal, {
    condition(component, id, action) {
        const requiredActions = ['insertToComposer', 'copy-message', 'send-message-direct', 'log-note-direct'];
        if (
            component.props.thread?.channel_type === 'ai_composer' && 
            !requiredActions.includes(id)
        ) {
            return false
        }
        return super.condition(component, id, action);
    }
})
