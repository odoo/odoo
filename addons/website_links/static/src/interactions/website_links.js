import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { addLoadingEffect } from '@web/core/utils/ui';
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { WebsiteLinksTagsWrapper } from "../js/tags_wrapper";

export class WebsiteLinks extends Interaction {
    static selector = ".o_website_links_create_tracked_url";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _notification: () => document.querySelector(".notification"),
        _notificationLinks: () => document.querySelector(".o_website_links_recent_links_notification"),
    };
    dynamicContent = {
        "#recent_links_sort_by a": {
            "t-on-click": this.onRecentLinksFilterChange,
            "t-att-class": (el) => ({
                "active": el.dataset.filter === this.currentFilter,
            }),
        },
        ".o_website_links_new_link_tracker": {
            "t-on-click": this.onCreateNewLinkTrackerClick,
        },
        "#o_website_links_link_tracker_form": {
            "t-on-submit.prevent": this.onFormSubmit,
        },
        ".btn_shorten_url_clipboard": {
            "t-on-click.prevent.withTarget": this.onCopyShortenUrl,
        },
        "#btn_shorten_url": {
            "t-att-class": () => ({
                "d-none": this.hideButtonShorten,
            }),
        },
        "#generated_tracked_link": {
            "t-att-class": () => ({
                "d-none": this.hideButtonShorten,
            }),
        },
        ".o_website_links_utm_forms": {
            "t-att-class": () => ({
                "d-none": this.hideButtonShorten,
            }),
        },
        _notification: {
            "t-out": () => this.notificationContent,
        },
        _notificationLinks: {
            "t-out": () => this.notificationLinksContent,
        },
    };

    setup() {
        this.hideButtonShorten = true;
        this.notificationContent = "";

        this.currentFilter = "newest";

        this.urlEl = document.querySelector("#url");
        this.labelEl = document.querySelector("#label");
    }

    start() {
        this.mountComponent(
            this.el.querySelector("#campaign-select-wrapper"),
            WebsiteLinksTagsWrapper,
            {
                placeholder: _t("e.g. June Sale, Paris Roadshow, ..."),
                model: "utm.campaign",
            });

        this.mountComponent(
            this.el.querySelector("#channel-select-wrapper"),
            WebsiteLinksTagsWrapper,
            {
                placeholder: _t("e.g. InMails, Ads, Social, ..."),
                model: "utm.medium",
            });

        this.mountComponent(
            this.el.querySelector("#source-select-wrapper"),
            WebsiteLinksTagsWrapper,
            {
                placeholder: _t("e.g. LinkedIn, Facebook, Leads, ..."),
                model: "utm.source",
            });

        this.recentLinksEl = document.querySelector("#o_website_links_recent_links");
        this.getRecentLinks();

        const tooltipEl = document.querySelector("[data-bs-toggle='tooltip']");
        if (tooltipEl) {
            const bsTooltip = window.Tooltip.getOrCreateInstance(tooltipEl)
            this.registerCleanup(() => bsTooltip.dispose());
        }
    }

    async getRecentLinks() {
        const result = await this.waitFor(rpc('/website_links/recent_links', {
            filter: this.currentFilter,
            limit: 20,
        }));
        if (result) {
            result.reverse().forEach((link) => {
                this.addLink(link);
            });
            this.updateNotification();
            this.updateFilters();
        } else {
            const divEl = document.createElement("div");
            divEl.classList.add("alert", "alert-danger");
            divEl.innerText = _t("Unable to get recent links");
            this.insert(divEl, this.recentLinksEl);
        }
    }

    addLink(link) {
        const wasEmpty = this.recentLinksEl.children.length === 0;
        this.renderAt("website_links.RecentLink", { link: link }, this.recentLinksEl, "afterbegin");

        const tooltipEl = document.querySelector(".link-tooltip");
        if (tooltipEl) {
            const bsTooltip = window.Tooltip.getOrCreateInstance(tooltipEl)
            this.registerCleanup(() => bsTooltip.dispose());
        }

        if (wasEmpty) {
            this.updateNotification();
        }
    }

    removeLinks() {
        this.recentLinksEl.children.forEach((el) => el.remove());
    }

    updateFilters() {
        const dropdownBtns = document.querySelectorAll('#recent_links_sort_by a');
        dropdownBtns.forEach((button) => {
            if (button.dataset.filter === this.currentFilter) {
                document.querySelector('.o_website_links_sort_by').textContent = button.textContent;
            }
        });
    }

    updateNotification() {
        if (this.recentLinksEl.children.length === 0) {
            const divEl = document.createElement("div");
            divEl.classList.add("alert", "alert-info");
            divEl.innerText = _t("You don't have any recent links.");
            this.notificationLinksContent = divEl;
        } else {
            this.notificationLinksContent = "";
        }
    }

    onCopyShortenUrl(ev, currentTargetEl) {
        const tooltip = Tooltip.getOrCreateInstance(currentTargetEl, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "top",
        });
        const url = currentTargetEl.dataset.url;
        setTimeout(async () => await browser.navigator.clipboard.writeText(url));
        tooltip.show();
        setTimeout(() => tooltip.hide(), 1200);
    }

    onRecentLinksFilterChange(ev, currentTargetEl) {
        this.removeLinks();
        this.currentFilter = currentTargetEl.dataset.filter;
        this.getRecentLinks();
    }

    onCreateNewLinkTrackerClick() {
        if (!this.hideButtonShorten) {
            return;
        }
        this.hideButtonShorten = false;
        this.urlEl.value = "";
    }

    async onFormSubmit(ev) {
        const generateLinkTrackerBtn = document.querySelector("#btn_shorten_url");
        if (this.hideButtonShorten = true) {
            return;
        }
        const restoreLoadingBtn = addLoadingEffect(generateLinkTrackerBtn);

        ev.stopPropagation();

        // Get URL and UTMs
        const campaignInputEl = document.querySelector("input[name='campaign-select']");
        const mediumInputEl = document.querySelector("input[name='medium-select']");
        const sourceInputEl = document.querySelector("input[name='source-select']");

        const result = await this.waitFor(rpc("/website_links/new", {
            url: this.urlEl.value,
            label: this.labelEl.value,
            campaign_id: parseInt(campaignInputEl.value) || undefined,
            medium_id: parseInt(mediumInputEl.value) || undefined,
            source_id: parseInt(sourceInputEl.value) || undefined,
        }))

        restoreLoadingBtn();
        if ("error" in result) {
            // Handle errors
            const divEl = document.createElement("div");
            divEl.classList.add("alert", "alert-danger");
            divEl.innerText =
                result.error === "empty_url" ? "The URL is empty."
                    : result.error === "url_not_found" ? "URL not found (404)"
                        : "An error occur while trying to generate your link. Try again later.";
            this.notificationContent = divEl;
        } else {
            // Link generated, clean the form and show the link
            const link = result[0];
            this.hideButtonShorten = true;

            document.querySelector(".copy-to-clipboard").dataset.clipboardText = link.short_url;
            document.querySelector("#short-url-host").textContent = link.short_url_host;
            document.querySelector("#o_website_links_code").textContent = link.code;

            this.addLink(link);

            // Clean notifications, URL and UTM selects
            this.notificationContent = "";
            campaignInputEl.value = "";
            mediumInputEl.value = "";
            sourceInputEl.value = "";
            this.labelEl.value = "";
        }
    }
}

registry
    .category("public.interactions")
    .add("website_links.website_links", WebsiteLinks);
