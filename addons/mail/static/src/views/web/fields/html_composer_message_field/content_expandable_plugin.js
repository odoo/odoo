import { Plugin } from "@html_editor/plugin";
import { renderToElement } from "@web/core/utils/render";

export class ContentExpandablePlugin extends Plugin {
    static id = "contentexpandable";
    resources = {
        start_edition_handlers: this.insertReplyContent.bind(this),
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
    };

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

    onClickViewButton() {
        const ele = this.editable.querySelector(".o_mail_reply_content");
        if (!ele) {
            return;
        }
        ele.lastElementChild.classList.toggle("d-none");
        this.editable.focus();
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
