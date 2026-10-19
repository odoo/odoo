import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class MailGroupMessage extends Interaction {
    static selector = ".o_mg_message";
    dynamicContent = {
        ".o_mg_link_hide": {
            "t-on-click.prevent.stop": () => this.isShown = false,
            "t-att-class": () => ({ "d-none": !this.isShown }),
        },
        ".o_mg_link_show": {
            "t-on-click.prevent.stop": () => this.isShown = true,
            "t-att-class": () => ({ "d-none": this.isShown }),
        },
        ".o_mg_link_content": { "t-att-class": () => ({ "d-none": this.isShown }) },
        "button.o_mg_read_more": { "t-on-click": this.onReadMoreClick },
    };

    setup() {
        this.isShown = true;

        // By default hide the mention of the previous email for which we reply
        // And add a button "Read more" to show the mention of the parent email
        const quoted = this.el.querySelectorAll(".card-body *[data-o-mail-quote]");
        if (quoted.length > 0)  {
            const readMore = document.createElement("button");
            readMore.classList.add("btn", "btn-light", "btn-sm", "ms-1");
            readMore.innerText = ". . .";
            quoted[0].before(readMore);
            readMore.addEventListener("click", () => quoted.forEach((node) => node.classList.toggle("visible")));
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    async onReadMoreClick(ev) {
        const data = await this.waitFor(rpc(ev.target.getAttribute("href"), {
            last_displayed_id: ev.target.dataset.listDisplayedId,
        }));
        if (data) {
            const threadContainer = ev.target.closest(".o_mg_replies")?.querySelector("ul.list-unstyled");
            if (threadContainer) {
                const messages = threadContainer.querySelectorAll(":scope > li.media");
                let lastMessage = messages[messages.length - 1];
                const newMessages = data.querySelector("ul.list-unstyled").querySelectorAll(":scope > li.media");
                for (const newMessage in newMessages) {
                    this.insert(newMessage, lastMessage, "afterend");
                    lastMessage = newMessage;
                }
                this.insert(data.querySelector(".o_mg_read_more").parentElement, threadContainer);
            }
            ev.target.parentElement.remove();
        }
    }
}

registry
    .category("public.interactions")
    .add("mail_group.mail_group_message", MailGroupMessage);
