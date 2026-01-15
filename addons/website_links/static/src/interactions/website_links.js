import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { addLoadingEffect } from "@web/core/utils/ui";
import { browser } from "@web/core/browser/browser";
import { WebsiteLinksTagsWrapper } from "@website_links/components/website_links_tags_wrapper";

class WebsiteLinks extends Interaction {
    static selector = ".o_website_links_create_tracked_url";
    dynamicContent = {
        "#recent_links_sort_by a": {
            "t-on-click": this.onRecentLinksFilterChange,
        },
        ".o_website_links_new_link_tracker": {
            "t-on-click": this.onCreateNewLinkTrackerClick,
        },
        "#o_website_links_link_tracker_form": {
            "t-on-submit.prevent": this.onFormSubmit,
        },
        ".btn_shorten_url_clipboard": {
            "t-on-click.prevent": this.onCopyShortURL,
        },
        "#campaign-select-wrapper": {
            "t-component": () => [
                WebsiteLinksTagsWrapper,
                {
                    placeholder: _t("e.g. June Sale, Paris Roadshow, ..."),
                    model: "utm.campaign",
                },
            ],
        },
        "#channel-select-wrapper": {
            "t-component": () => [
                WebsiteLinksTagsWrapper,
                {
                    placeholder: _t("e.g. InMails, Ads, Social, ..."),
                    model: "utm.medium",
                },
            ],
        },
        "#source-select-wrapper": {
            "t-component": () => [
                WebsiteLinksTagsWrapper,
                {
                    placeholder: _t("e.g. LinkedIn, Facebook, Leads, ..."),
                    model: "utm.source",
                },
            ],
        },
    };

    setup() {
        this.linkEls = [];
        this.urls = new Set();
        this.notificationEls = new Map();
        this.formNotificationEl = this.el.querySelector(".notification");
        this.listNotificationEl = this.el.querySelector(
            ".o_website_links_recent_links_notification"
        );
        this.listContainerEl = this.el.querySelector("#o_website_links_recent_links");
        this.getRecentLinks("newest");
    }

    onCopyShortURL(event) {
        const copyBtnEl = event.currentTarget;
        const tooltip = window.Tooltip.getOrCreateInstance(copyBtnEl, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "top",
        });
        browser.navigator.clipboard.writeText(copyBtnEl.dataset.url);
        tooltip.show();
        this.waitForTimeout(() => tooltip.hide(), 1200);
    }

    onRecentLinksFilterChange(event) {
        this.getRecentLinks(event.currentTarget.dataset.filter);
    }

    onCreateNewLinkTrackerClick() {
        const utmFormEl = this.el.querySelector(".o_website_links_utm_forms");
        if (!utmFormEl.classList.contains("d-none")) {
            return;
        }
        utmFormEl.classList.remove("d-none");
        this.el.querySelector("#generated_tracked_link").classList.add("d-none");
        this.el.querySelector("#btn_shorten_url").classList.remove("d-none");
        this.el.querySelector("input#url").value = "";
    }

    async onFormSubmit(event) {
        const generateLinkTrackerBtnEl = this.el.querySelector("#btn_shorten_url");
        if (generateLinkTrackerBtnEl.classList.contains("d-none")) {
            return;
        }
        const restoreLoadingBtn = addLoadingEffect(generateLinkTrackerBtnEl);
        this.registerCleanup(restoreLoadingBtn);
        event.stopPropagation();

        // Get URL and UTMs
        const campaignInputEl = this.el.querySelector("input[name='campaign-select']");
        const mediumInputEl = this.el.querySelector("input[name='medium-select']");
        const sourceInputEl = this.el.querySelector("input[name='source-select']");

        const labelEl = this.el.querySelector("#label");
        const params = { label: labelEl.value || undefined };
        params.url = this.el.querySelector("input#url").value;
        if (campaignInputEl.value !== "") {
            params.campaign_id = parseInt(campaignInputEl.value);
        }
        if (mediumInputEl.value !== "") {
            params.medium_id = parseInt(mediumInputEl.value);
        }
        if (sourceInputEl.value !== "") {
            params.source_id = parseInt(sourceInputEl.value);
        }

        const result = await this.waitFor(rpc("/website_links/new", params));
        restoreLoadingBtn();
        if ("error" in result) {
            // Handle errors
            if (result.error === "empty_url") {
                this.addNotification(
                    this.formNotificationEl,
                    "The URL is empty",
                    "alert-danger",
                    "form-submit"
                );
            } else if (result.error === "url_not_found") {
                this.addNotification(
                    this.formNotificationEl,
                    "URL not found (404)",
                    "alert-danger",
                    "form-submit"
                );
            } else {
                this.addNotification(
                    this.formNotificationEl,
                    "An error occurred while trying to generate your link. Try again later.",
                    "alert-danger",
                    "form-submit"
                );
            }
        } else {
            // Link generated, clean the form and show the link
            const link = result[0];

            this.el.querySelector("#generated_tracked_link").classList.remove("d-none");
            this.el.querySelector("#btn_shorten_url").classList.add("d-none");
            this.el.querySelector(".copy-to-clipboard").dataset.clipboardText = link.short_url;
            this.el.querySelector("#short-url-host").textContent = link.short_url_host;
            this.el.querySelector("#o_website_links_code").textContent = link.code;

            this.addLink(link);

            // Clean notifications, URL and UTM selects
            this.removeNotification("form-submit");
            campaignInputEl.value = "";
            mediumInputEl.value = "";
            sourceInputEl.value = "";
            labelEl.value = "";
            this.el.querySelector(".o_website_links_utm_forms").classList.add("d-none");
        }
    }

    async getRecentLinks(filter) {
        this.removeLinks();
        try {
            const links = await this.waitFor(
                rpc("/website_links/recent_links", {
                    filter,
                    limit: 20,
                })
            );
            links.reverse();
            for (const link of links) {
                this.addLink(link);
            }
            this.updateNotification();
            this.updateFilters(filter);
        } catch {
            this.addNotification(
                this.listNotificationEl,
                "Unable to get recent links.",
                "alert-danger",
                "get-recent-links"
            );
        }
    }

    addLink(link) {
        if (this.urls.has(link.short_url)) {
            return;
        }
        const hadLinks = this.linkEls.length > 0;
        this.linkEls.push(
            ...this.renderAt("website_links.RecentLink", link, this.listContainerEl, "afterbegin")
        );
        this.urls.add(link.short_url);
        if (!hadLinks) {
            this.updateNotification();
        }
    }

    removeLinks() {
        for (const linkBox of this.linkEls) {
            linkBox.remove();
        }
        this.linkEls = [];
        this.urls.clear();
    }

    updateNotification() {
        if (!this.linkEls.length) {
            this.addNotification(
                this.listNotificationEl,
                "You don't have any recent links.",
                "alert-info",
                "no-links"
            );
        } else {
            this.removeNotification("no-links");
        }
    }

    updateFilters(filter) {
        const dropdownBtnEls = this.el.querySelectorAll("#recent_links_sort_by a");
        for (const buttonEl of dropdownBtnEls) {
            const isCurrentFilter = buttonEl.dataset.filter === filter;
            if (isCurrentFilter) {
                this.el.querySelector(".o_website_links_sort_by").textContent =
                    buttonEl.textContent;
            }
            buttonEl.classList.toggle("active", isCurrentFilter);
        }
    }

    addNotification(containerEl, message, className, key) {
        this.removeNotification(key);
        const notificationEl = document.createElement("div");
        notificationEl.textContent = _t(message);
        notificationEl.classList.add("alert", className);
        this.insert(notificationEl, containerEl);
        this.notificationEls.set(key, notificationEl);
    }

    removeNotification(key) {
        this.notificationEls.get(key)?.remove();
        this.notificationEls.delete(key);
    }
}

registry.category("public.interactions").add("website_links.WebsiteLinks", WebsiteLinks);
