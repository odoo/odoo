import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { useAutofocus } from "@web/core/utils/hooks";
import { useState, useEffect, useRef } from "@odoo/owl";
import { ChatGPTDialog } from "./chatgpt_dialog";

export class ChatGPTPromptDialog extends ChatGPTDialog {
    static template = "html_editor.ChatGPTPromptDialog";
    static props = {
        ...super.props,
        initialPrompt: { type: String, optional: true },
    };
    static defaultProps = {
        initialPrompt: "",
    };

    setup() {
        super.setup();
        this.assistantAvatarUrl = `${browser.location.origin}/web_editor/static/src/img/odoobot_transparent.png`;
        this.userAvatarUrl = `${
            browser.location.origin
        }/web/image?model=res.users&field=avatar_128&id=${encodeURIComponent(user.userId)}`;
        this.state = useState({
            ...this.state,
            prompt: this.props.initialPrompt,
            conversationHistory: [
                {
                    role: "system",
                    content:
                        "You are a helpful assistant, your goal is to help the user write their document.",
                },
                {
                    role: "assistant",
                    content: "What do you need ?",
                },
            ],
            messages: [],
        });
        this.promptInputRef = useRef("promptInput");
        useAutofocus({ refName: "promptInput", mobile: true });
        useEffect(
            () => {
                // Resize the textarea to fit its content.
                this.promptInputRef.el.style.height = 0;
                this.promptInputRef.el.style.height = this.promptInputRef.el.scrollHeight + "px";
            },
            () => [this.state.prompt]
        );
    }

    onTextareaKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            this.submitPrompt(ev);
        }
    }

    submitPrompt(ev) {
        this.freezeInput();
        ev.preventDefault();
        const prompt = this.state.prompt;
        this.state.messages.push({ author: "user", text: prompt });
        const messageId = new Date().getTime();
        const conversation = { role: "user", content: prompt };
        this.state.conversationHistory.push(conversation);
        this.state.messages.push({ author: "assistant", id: messageId });
        this.state.prompt = "";
        this.generate(prompt, (content, isError) => {
            if (isError) {
                // There was an error, remove the prompt from the history.
                this.state.conversationHistory = this.state.conversationHistory.filter(
                    (c) => c !== conversation
                );
            } else {
                // There was no error, add the response to the history.
                this.state.conversationHistory.push({ role: "assistant", content });
            }
            const messageIndex = this.state.messages.findIndex((m) => m.id === messageId);
            this.state.messages[messageIndex] = {
                author: "assistant",
                text: content,
                isError,
                id: messageId,
            };
            this.unfreezeInput();
        });
    }

    freezeInput() {
        this.promptInputRef.el.setAttribute("disabled", "");
    }

    unfreezeInput() {
        this.promptInputRef.el.removeAttribute("disabled");
        this.promptInputRef.el.focus();
    }

    /**
     * @override
     */
    _cancel() {
        this.freezeInput();
        super._cancel();
    }

    /**
     * @override
     */
    _confirm() {
        this.freezeInput();
        super._confirm();
    }
}
