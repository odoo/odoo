import { Plugin } from "@html_editor/plugin";
import { parseHTML } from "@html_editor/utils/html";

export class ContentExpandablePlugin extends Plugin {
    static id = "contentexpandable";
    static dependencies = ["dom", "history"];
    resources = {
        start_edition_handlers: this.insertReplyContent.bind(this),
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
    };

    insertReplyContent() {
        const mailQuoteElement = this.editable.querySelectorAll('*[data-o-mail-quote="1"]');
        for (const element of mailQuoteElement) {
            element.removeAttribute("data-o-mail-quote");
        }
        const paragraph = parseHTML(
            this.document,
            `<p><br/><button id="viewMore" contenteditable="false" class="badge rounded-pill border-0 m-1 py-0 px-1"><i class="fa fa-ellipsis-h fa-lg"/></button></p>`
        );
        const button = paragraph.querySelector("#viewMore");
        this.addDomListener(button, "click", () => this.onClickViewButton());
        this.dependencies.dom.insert(paragraph);
        this.dependencies.history.addStep();
    }

    onClickViewButton() {
        const ele = this.editable.querySelector(".o_mail_hidden_content");
        if (!ele) {
            return;
        }
        if (ele.classList.contains("d-none")) {
            ele.classList.remove("d-none");
        } else {
            ele.classList.add("d-none");
        }
        this.editable.focus();
    }

    cleanForSave(root) {
        root.querySelector("button#viewMore")?.remove();
        const ele = root.querySelector(".o_mail_hidden_content");
        if (!ele) {
            return;
        }
        ele.setAttribute("data-o-mail-quote", "1");
        ele.removeAttribute("class");
    }
}
