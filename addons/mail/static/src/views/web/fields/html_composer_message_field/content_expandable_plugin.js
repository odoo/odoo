import { Plugin } from "@html_editor/plugin";
import { renderToElement } from "@web/core/utils/render";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class ContentExpandablePlugin extends Plugin {
    static id = "contentexpandable";
    resources = {
        start_edition_handlers: this.insertReplyContent.bind(this),
        delete_backward_overrides: this.handleDelete.bind(this),
        delete_backward_line_overrides: this.handleDelete.bind(this),
        delete_backward_word_overrides: this.handleDelete.bind(this),
        delete_forward_overrides: this.handleDelete.bind(this),
        delete_forward_line_overrides: this.handleDelete.bind(this),
        delete_forward_word_overrides: this.handleDelete.bind(this),
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
    };

    handleDelete(range) {
        const { startContainer, endContainer } = range;
        if (
            closestElement(startContainer).querySelector(".o-mail-Message-viewMore-btn") ||
            closestElement(endContainer).querySelector(".o-mail-Message-viewMore-btn")
        ) {
            return true;
        }
    }

    insertReplyContent() {
        const ele = this.editable.querySelector(".o_mail_reply_content");
        if (!ele) {
            return;
        }
        const mailQuoteElement = this.editable.querySelectorAll('*[data-o-mail-quote="1"]');
        for (const element of mailQuoteElement) {
            element.removeAttribute("data-o-mail-quote");
            element.removeAttribute("style");
        }
        const buttonTemplate = renderToElement("mail.ExpandableButton");
        const button = buttonTemplate.querySelector(".o-mail-Message-viewMore-btn");
        this.addDomListener(button, "click", this.onClickViewButton);
        ele.prepend(buttonTemplate);
    }

    onClickViewButton(ev) {
        const ele = this.editable.querySelector(".o_mail_reply_content");
        if (!ele) {
            return;
        }
        ele.lastElementChild.classList.toggle("d-none");
        closestElement(ev.target, "div").remove();
    }

    cleanForSave(root) {
        const ele = root.querySelector(".o_mail_reply_content");
        if (!ele) {
            return;
        }
        ele.querySelector(".o-mail-Message-viewMore-btn")?.parentElement.remove();
        ele.lastElementChild.classList.remove("d-none");
        ele.setAttribute("data-o-mail-quote", "1");
    }
}
