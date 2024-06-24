import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillDestroy, status, markup } from "@odoo/owl";

const POSTPROCESS_GENERATED_CONTENT = (content) => {
    const lines = content.split("\n").filter((line) => line.trim().length);
    const fragment = document.createDocumentFragment();
    let parentUl, parentOl;
    let lineIndex = 0;
    for (const line of lines) {
        if (line.trim().startsWith("- ")) {
            // Create or continue an unordered list.
            parentUl = parentUl || document.createElement("ul");
            const li = document.createElement("li");
            li.innerText = line.trim().slice(2);
            parentUl.appendChild(li);
        } else if (
            (parentOl && line.startsWith(`${parentOl.children.length + 1}. `)) ||
            (!parentOl && line.startsWith("1. ") && lines[lineIndex + 1]?.startsWith("2. "))
        ) {
            // Create or continue an ordered list (only if the line starts
            // with the next number in the current ordered list (or 1 if no
            // ordered list was in progress and it's followed by a 2).
            parentOl = parentOl || document.createElement("ol");
            const li = document.createElement("li");
            li.innerText = line.slice(line.indexOf(".") + 2);
            parentOl.appendChild(li);
        } else {
            // Insert any list in progress, and a new block for the current
            // line.
            [parentUl, parentOl].forEach((list) => list && fragment.appendChild(list));
            parentUl = parentOl = undefined;
            const block = document.createElement(line.startsWith("Title: ") ? "h2" : "p");
            block.innerText = line;
            fragment.appendChild(block);
        }
        lineIndex += 1;
    }
    [parentUl, parentOl].forEach((list) => list && fragment.appendChild(list));
    return fragment;
};

export class ChatGPTDialog extends Component {
    static template = "";
    static components = { Dialog };
    static props = {
        insert: Function,
        close: Function,
    };

    setup() {
        this.notificationService = useService("notification");
        this.state = useState({ selectedMessageId: null });
        onWillDestroy(() => this.pendingRpcPromise?.abort());
    }

    selectMessage(ev) {
        this.state.selectedMessageId = +ev.currentTarget.getAttribute("data-message-id");
    }

    insertMessage(ev) {
        this.selectMessage(ev);
        this._confirm();
    }

    formatContent(content) {
        return markup(
            [...POSTPROCESS_GENERATED_CONTENT(content).childNodes]
                .map((child) => {
                    // Escape all text.
                    const nodes = new Set(
                        [...child.querySelectorAll("*")].flatMap((node) => node.childNodes)
                    );
                    nodes.forEach((node) => {
                        if (node.nodeType === Node.TEXT_NODE) {
                            node.textContent = escape(node.textContent);
                        }
                    });
                    return child.outerHTML;
                })
                .join("")
        );
    }

    generate(prompt, callback) {
        const protectedCallback = (...args) => {
            if (status(this) !== "destroyed") {
                delete this.pendingRpcPromise;
                return callback(...args);
            }
        };
        this.pendingRpcPromise = rpc(
            "/web_editor/generate_text",
            {
                prompt,
                conversation_history: this.state.conversationHistory,
            },
            { shadow: true }
        );
        return this.pendingRpcPromise
            .then((content) => protectedCallback(content))
            .catch((error) => protectedCallback(_t(error.data?.message || error.message), true));
    }

    _cancel() {
        this.props.close();
    }

    _confirm() {
        try {
            this.props.close();
            const text = this.state.messages.find(
                (message) => message.id === this.state.selectedMessageId
            )?.text;
            this.notificationService.add(_t("Your content was successfully generated."), {
                title: _t("Content generated"),
                type: "success",
            });
            this.props.insert(POSTPROCESS_GENERATED_CONTENT(text || ""));
        } catch (e) {
            this.props.close();
            throw e;
        }
    }
}
