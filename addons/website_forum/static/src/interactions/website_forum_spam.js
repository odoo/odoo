import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";
import { KeepLast } from "@web/core/utils/concurrency";
import { cloneContentEls } from "@website/js/utils";

export class WebsiteForumSpam extends Interaction {
    static selector = ".o_wforum_moderation_queue";
    dynamicContent = {
        ".o_wforum_select_all_spam": { "t-on-click": this.onSelectAllSpamClick },
        ".o_wforum_mark_spam": { "t-on-click": this.locked(this.onMarkSpamClick, true) },
        "#spamSearch": { "t-on-input": this.debounced(this.onSpamSearchInput, 200) },
    };

    setup() {
        this.spamIDs = JSON.parse(
            this.el.ownerDocument.querySelector(".modal[data-spam-ids]")?.dataset.spamIds || "[]"
        );
        this.keepLast = new KeepLast();
    }

    onSelectAllSpamClick() {
        const inputEls = this.el.querySelectorAll(".modal .tab-pane.active input");
        inputEls.forEach((el) => el.checked = true);
    }

    /**
     * @param {Event} ev
     */
    async onSpamSearchInput(ev) {
        const toSearch = ev.target.value;
        const posts = await this.keepLast.add(
            this.waitFor(this.services.orm.searchRead(
                "forum.post",
                [["id", "in", this.spamIDs],
                    "|",
                ["name", "ilike", toSearch],
                ["content", "ilike", toSearch]],
                ["name", "content"]
            ))
        );
        const postSpamEl = this.el.querySelector("div.post_spam");
        const postSpamElContent = postSpamEl.children;
        postSpamEl.replaceChildren();
        this.registerCleanup(() => postSpamEl.replaceChildren(postSpamElContent));
        if (!posts.length) {
            return;
        }
        Object.values(posts).forEach((post) => {
            const childEl = cloneContentEls(post.content).firstElementChild;
            post.content = childEl.textContent.substring(0, 250);
        });
        // No need for cleanup, it's already done above.
        this.renderAt("website_forum.spam_search_name", { posts }, postSpamEl);
    }

    async onMarkSpamClick() {
        const key = this.el.querySelector(".modal .tab-pane.active").dataset.key;
        const inputEls = this.el.querySelectorAll(".modal .tab-pane.active input.form-check-input:checked");
        const values = Array.from(inputEls).map((inputEl) => parseInt(inputEl.value));
        await this.waitFor(this.services.orm.call("forum.post", "mark_as_offensive_batch", [
            this.spamIDs,
            key,
            values,
        ]));
        browser.location.reload();
    }
}

registry
    .category("public.interactions")
    .add("website_forum.website_forum_spam", WebsiteForumSpam);
