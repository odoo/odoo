import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillDestroy, status, markup } from "@odoo/owl";

const POSTPROCESS_GENERATED_CONTENT = (content, baseContainer) => {
    let lines = content.split("\n");
    if (baseContainer.toUpperCase() === "P") {
        // P has a margin bottom which is used as an interline, no need to
        // keep empty lines in that case.
        lines = lines.filter((line) => line.trim().length);
    }
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
        } else if (line.trim().length === 0) {
            const emptyLine = document.createElement("DIV");
            emptyLine.append(document.createElement("BR"));
            fragment.appendChild(emptyLine);
        } else {
            // Insert any list in progress, and a new block for the current
            // line.
            [parentUl, parentOl].forEach((list) => list && fragment.appendChild(list));
            parentUl = parentOl = undefined;
            const block = document.createElement(line.startsWith("Title: ") ? "h2" : baseContainer);
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
        insert: { type: Function },
        close: { type: Function },
        sanitize: { type: Function },
        baseContainer: { type: String, optional: true },
    };
    static defaultProps = {
        baseContainer: "DIV",
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
        const fragment = POSTPROCESS_GENERATED_CONTENT(content, this.props.baseContainer);
        let result = "";
        for (const child of fragment.children) {
            this.props.sanitize(child, { IN_PLACE: true });
            result += child.outerHTML;
        }
        return markup(result);
    }

    generate(prompt, callback) {
        const protectedCallback = (...args) => {
            if (status(this) !== "destroyed") {
                delete this.pendingRpcPromise;
                return callback(...args);
            }
        };
        this.pendingRpcPromise = rpc(
            "/html_editor/generate_text",
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
            const fragment = POSTPROCESS_GENERATED_CONTENT(text || "", this.props.baseContainer);
            this.props.sanitize(fragment, { IN_PLACE: true });
            this.props.insert(fragment);
        } catch (e) {
            this.props.close();
            throw e;
        }
    }
}
