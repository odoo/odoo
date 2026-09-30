import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class WebsiteProfileForumActivity extends Interaction {
    static selector = ".o_wprofile_forum_activity";
    dynamicContent = {
        "#o_wprofile_forum_activity_filter li a": {
            "t-on-click.withTarget": (ev, currentTargetEl) =>
                this.selectTab(
                    currentTargetEl.getAttribute("href").split("_").at(-1),
                    currentTargetEl.text
                ),
        },
        ".o_wprofile_forum_activity_search_question": {
            "t-att-class": () => ({ "d-none": this.activeTab !== "question" }),
        },
        ".o_wprofile_forum_activity_search_answer": {
            "t-att-class": () => ({ "d-none": this.activeTab !== "answer" }),
        },
        ".o_wprofile_forum_activity_filter_label": {
            "t-out": () => this.activeTabLabel,
        },
    };

    setup() {
        const activeTab = this.el.dataset.activeTab;
        this.selectTab(
            activeTab,
            document.querySelector(
                `#o_wprofile_forum_activity_filter li a[href='#o_wprofile_forum_activity_tab_${activeTab}']`
            ).textContent
        );
    }

    selectTab(tab, activeTabLabel) {
        this.activeTab = tab;
        this.activeTabLabel = activeTabLabel;
    }
}

registry
    .category("public.interactions")
    .add("website_forum.wprofile_forum_activity", WebsiteProfileForumActivity);
