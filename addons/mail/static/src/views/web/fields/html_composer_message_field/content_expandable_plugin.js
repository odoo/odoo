import { Plugin } from "@html_editor/plugin";

export class ContentExpandablePlugin extends Plugin {
    static id = "contentexpandable";
    static dependencies = ["dom", "history"];
    resources = {
        start_edition_handlers: this.insertReplyContent.bind(this),
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
    };

    insertReplyContent() {
        const ab = this.editable.querySelectorAll('*[data-o-mail-quote="1"]')
        for (const el of ab){
            el.removeAttribute("data-o-mail-quote")
        }
        const iEl = document.createElement("i");
        const button = document.createElement("button");
        const paragraph = document.createElement("p");
        iEl.className = "fa fa-ellipsis-h fa-lg";
        button.className = "badge rounded-pill border-0 m-1 py-0 px-1";
        button.setAttribute('contenteditable',false)
        button.appendChild(iEl);
        paragraph.appendChild(document.createElement("br"));
        paragraph.appendChild(button);
        this.addDomListener(button, "click", () => this.onClickViewButton());
        this.dependencies.dom.insert(paragraph);
        this.dependencies.history.addStep();

    }

    onClickViewButton() {
        const ele = this.editable.querySelector(".o_mail_hidden_content");
        if (!ele){
            return
        }
        if (ele.classList.contains("d-none")) {
            ele.classList.remove("d-none");
        } else {
            ele.classList.add("d-none");
        }
        this.editable.focus()
    }

    cleanForSave(root) {
        root.querySelector("button")?.remove()
        const ele = root.querySelector(".o_mail_hidden_content")
        if (!ele){
            return
        }
        ele.setAttribute("data-o-mail-quote", "1")
        ele.removeAttribute("class");
    }
}
