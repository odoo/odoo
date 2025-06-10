import { patch } from "@web/core/utils/patch";
import { HtmlComposer } from "./html_composer";
import { ChatWindow } from "@mail/core/common/chat_window";

Object.assign(ChatWindow.components, { HtmlComposer });

patch(ChatWindow.prototype, {
    onKeydown(ev) {
        if (
            document.querySelector(".o-mail-SuggestionList") &&
            (ev.key === "Tab" ||
                ev.key === "Enter" ||
                ev.key === "ArrowUp" ||
                ev.key === "ArrowDown")
        ) {
            return;
        }
        super.onKeydown(ev);
    },
});
