/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class BlogTableOfContents extends Interaction {
    static selector = ".o_wblog_toc";

    setup() {
        this.navEl = this.el.querySelector(".o_wblog_toc_nav");
        this.contentEl = document.querySelector("#o_wblog_post_content .o_wblog_post_content_field");
        if (!this.navEl || !this.contentEl) {
            return;
        }
        this.offsets = [];
        this.targets = [];
        this.activeTarget = null;
    }

    start() {
        if (!this.navEl || !this.contentEl) {
            return;
        }

        this.generateTOC();

        if (this.targets.length) {
            this.addListener(window, "scroll", this.process.bind(this));
            // Delay initial process to ensure layout is complete
            setTimeout(() => this.process(), 100);
        } else {
            this.el.classList.add("d-none");
        }
    }

    generateTOC() {
        const headings = this.contentEl.querySelectorAll("h2, h3, h4, h5, h6");
        this.navEl.innerHTML = "";
        if (!headings.length) {
            return;
        }

        const listGroup = document.createElement("div");
        listGroup.className = "list-group list-group-flush";

        headings.forEach((heading, i) => {
            if (!heading.id) {
                heading.id = `heading-${i}-${heading.textContent.toLowerCase().replace(/[^\w]+/g, "-")}`;
            }

            const level = parseInt(heading.tagName[1]) - 2;
            const link = document.createElement("a");
            link.href = `#${heading.id}`;
            link.textContent = heading.textContent.trim();
            link.className = `list-group-item list-group-item-action o_wblog_toc_link o_wblog_toc_link_${level} bg-transparent border-0 position-relative`;

            listGroup.appendChild(link);
            this.targets.push(`#${heading.id}`);
        });

        this.navEl.appendChild(listGroup);
        this.refresh();
    }

    refresh() {
        this.offsets = this.targets.map(target => {
            const el = document.querySelector(target);
            return el ? el.getBoundingClientRect().top + window.scrollY : 0;
        });
    }

    process() {
        if (!this.offsets.length) {
            return;
        }

        const scrollTop = window.scrollY + 120;

        if (scrollTop < this.offsets[0]) {
            this.activate(this.targets[0]);
            return;
        }

        for (let i = this.offsets.length; i--;) {
            if (scrollTop >= this.offsets[i]) {
                if (this.activeTarget !== this.targets[i]) {
                    this.activate(this.targets[i]);
                }
                return;
            }
        }
    }

    activate(target) {
        this.activeTarget = target;
        this.clear();
        const link = this.navEl.querySelector(`[href="${target}"]`);
        if (link) {
            link.classList.add("active");
        }
    }

    clear() {
        for (const link of this.navEl.querySelectorAll(".list-group-item")) {
            link.classList.remove("active");
        }
    }
}

registry.category("public.interactions").add("website_blog.toc", BlogTableOfContents);
