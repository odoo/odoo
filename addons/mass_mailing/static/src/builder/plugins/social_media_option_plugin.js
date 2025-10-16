import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC, TITLE_LAYOUT_SIZE } from "@html_builder/utils/option_sequence";
import { SocialMediaLinks } from "../options/social_media_links";
import { SocialMediaOptions } from "../options/social_media_option";
import { renderToElement } from "@web/core/utils/render";
import { BuilderAction } from "@html_builder/core/builder_action";
import { uniqueId } from "@web/core/utils/functions";
import { ResCompanyUpdateDialog } from "../components/company_update_dialog";
import { setAttributes } from "@web/core/utils/xml";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";

const LINK_OPTIONS_CLASSLIST = [
    "rounded",
    "rounded-circle",
    "rounded-empty-circle",
    "shadow-sm",
    "fa-stack",
    "small_social_icon",
    "fa-2x",
];

const LINKS_CONTAINER_SELECTOR = ".s_social_media_links";

class MassMailingSocialMediaOptionPlugin extends Plugin {
    static id = "massMailingSocialMediaOptionPlugin";
    static shared = [
        "addMedia",
        "fetchRecordedSocialMedia",
        "getMedias",
        "removeMedia",
        "renderPlaceholderEl",
        "renderSocialMediaLink",
        "renderTitleEl",
        "reorderSocialMediaLinks",
    ];
    static dependencies = ["builderActions", "history", "overlayButtons"];

    resources = {
        builder_options: [
            withSequence(TITLE_LAYOUT_SIZE, SocialMediaOptions),
            withSequence(SNIPPET_SPECIFIC, SocialMediaLinks),
        ],
        builder_actions: {
            AddSocialMediaLinkAction,
            ChangeCompanyAction,
            RemoveCustomSocialMediaLinkAction,
            ToggleSocialMediaLinkAction,
            UpdateSocialMediaLinksAction,
            UpdateTitlePositionAction,
        },
        so_content_addition_selector: [".s_social_media"],
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        content_editable_selectors: [
            ".s_social_media a > i",
            ".s_social_media .s_social_media_title",
        ],
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.normalize.bind(this),
        replace_media_dialog_params_handlers: this.applyIconsMediaDialogParams.bind(this),
    };

    setup() {
        this.medias = {};
        this.fetchRecordedSocialMedia(user.activeCompany?.id);
    }

    /** @returns {Array[string]} */
    get platforms() {
        return [
            "social_twitter",
            "social_facebook",
            "social_github",
            "social_linkedin",
            "social_youtube",
            "social_instagram",
            "social_tiktok",
            "social_discord",
        ];
    }

    get baseMediaValues() {
        return {
            facebook: "https://www.facebook.com/Odoo",
            instagram: "https://www.instagram.com/explore/tags/odoo/",
            twitter: "https://x.com/Odoo",
            linkedin: "https://www.linkedin.com/company/odoo",
            tiktok: "https://www.tiktok.com/@odoo",
        };
    }

    cleanForSave({ root }) {
        root.querySelectorAll(".o_social_snippet_empty_placeholder").forEach((element) =>
            element.remove()
        );
    }

    normalize(rootEl) {
        for (const snippet of selectElements(rootEl, ".s_social_media")) {
            snippet.querySelector(".o_social_snippet_dropped_placeholder")?.remove();
        }
        for (const linksContainer of selectElements(rootEl, LINKS_CONTAINER_SELECTOR)) {
            const snippet = closestElement(linksContainer, ".s_social_media");
            if (!snippet) {
                continue;
            }
            if (!linksContainer.firstElementChild) {
                if (!snippet.querySelector(".o_social_snippet_empty_placeholder")) {
                    snippet.append(this.renderPlaceholderEl());
                }
            } else {
                snippet.querySelector(".o_social_snippet_empty_placeholder")?.remove();
            }
        }
    }

    applyIconsMediaDialogParams(params) {
        if (
            params.node?.nodeType === Node.ELEMENT_NODE &&
            params.node.matches(".s_social_media .s_social_media_links .fa")
        ) {
            params.visibleTabs = ["ICONS"];
        }
    }

    renderPlaceholderEl() {
        return renderToElement("mass_mailing.social_media_placeholder");
    }

    renderTitleEl() {
        return renderToElement("mass_mailing.social_media_title");
    }

    async onSnippetDropped({ snippetEl }) {
        snippetEl = snippetEl.querySelector(".s_social_media") || snippetEl;
        if (!snippetEl.classList.contains("s_social_media")) {
            return;
        }
        const companyId = user.activeCompany?.id;
        snippetEl.setAttribute("data-company-id", companyId);
        const medias = await this.fetchRecordedSocialMedia(companyId);
        if (!Object.values(medias).length) {
            return this.handleNoSocialLinks(snippetEl, companyId);
        }

        let currentIndex = snippetEl.querySelectorAll("[data-platform]").length;

        for (const [platform, href] of Object.entries(medias)) {
            if (snippetEl.querySelector(`[data-platform="${platform}"]`) || !href) {
                continue;
            }
            this.dependencies.builderActions.getAction("toggleSocialMediaLink").apply({
                editingElement: snippetEl,
                params: { platform, href, getIndex: () => currentIndex },
            });
            currentIndex++;
        }
    }

    async handleNoSocialLinks(snippetEl, companyId) {
        if (companyId === undefined) {
            return;
        }
        const canWriteOnCompany = await user.checkAccessRight("res.company", "write");
        if (!canWriteOnCompany) {
            for (const [platform, href] of Object.entries(this.baseMediaValues)) {
                const newLinkElement = this.renderSocialMediaLink(platform, href);
                newLinkElement.dataset.platform = `customLink-${platform}`;
                snippetEl.querySelector(LINKS_CONTAINER_SELECTOR).append(newLinkElement);
            }
        } else {
            this.dependencies.overlayButtons.hideOverlayButtonsUi();
            const { promise, resolve } = Promise.withResolvers();
            this.services.dialog.add(
                ResCompanyUpdateDialog,
                {
                    resId: companyId,
                    onRecordSaved: (state) => {
                        const mediaList = this.platforms.map((platform) => [
                            platform,
                            state[platform],
                        ]);
                        const elements = [];
                        for (const [platform, href] of mediaList) {
                            if (!href) {
                                continue;
                            }
                            this.addMedia(platform, href);
                            elements.push(this.renderSocialMediaLink(platform, href));
                        }
                        snippetEl.querySelector(LINKS_CONTAINER_SELECTOR).append(...elements);
                    },
                },
                {
                    onClose: () => {
                        this.dependencies.overlayButtons.showOverlayButtonsUi();
                        resolve();
                    },
                }
            );
            await promise;
        }
    }

    renderSocialMediaLink(platform, href) {
        // remove `social_` prefix if necessary for the icon.
        const iconName = platform.startsWith("social_") ? platform.slice(7) : platform;
        const element = renderToElement("mass_mailing.social_media_link", {
            href: href || "",
            platform,
            icon: `fa-${iconName}`,
        });
        return element;
    }

    reorderSocialMediaLinks({ editingElement, platform, platformAfter }) {
        const elementAfter = editingElement.querySelector(`[data-platform="${platformAfter}"]`);
        const element = editingElement.querySelector(`[data-platform="${platform}"]`);
        if (elementAfter) {
            elementAfter.before(element);
        } else {
            editingElement.querySelector(LINKS_CONTAINER_SELECTOR).append(element);
        }
        this.dependencies.history.addStep();
    }

    /** @param {integer} companyId */
    async fetchRecordedSocialMedia(companyId) {
        if (!companyId) {
            return {};
        }
        const records = await this.services.orm.read("res.company", [companyId], this.platforms);
        const medias = {};
        for (const [fieldName, href] of Object.entries(records[0] ?? {})) {
            if (!href) {
                continue;
            }
            const matches = fieldName.match(/social_(\w+)/);
            if (matches) {
                const platform = matches[0];
                if (this.platforms.includes(platform)) {
                    medias[platform] = href;
                }
            }
        }
        this.medias = medias;
        return medias;
    }

    addMedia(platform, href) {
        this.medias[platform] = href;
    }

    getMedias() {
        return { ...this.medias };
    }

    removeMedia(platform) {
        delete this.medias[platform];
    }
}

class UpdateSocialMediaLinksAction extends BuilderAction {
    static id = "updateSocialMediaLinks";
    static dependencies = ["massMailingSocialMediaOptionPlugin"];
    apply({ editingElement, params: { mainParam: platform }, value }) {
        const linkToEdit = editingElement.querySelector(`a[data-platform='${platform}']`);
        if (!linkToEdit) {
            return;
        }
        linkToEdit.setAttribute("href", value);
    }
    getValue({ editingElement, params: { mainParam: platform } }) {
        const linkToEdit = editingElement.querySelector(`a[data-platform='${platform}']`);
        if (!linkToEdit) {
            return this.dependencies.massMailingSocialMediaOptionPlugin.getMedias()[platform] ?? "";
        }
        return linkToEdit.getAttribute("href");
    }
}

class UpdateTitlePositionAction extends BuilderAction {
    static id = "updateTitlePosition";
    static dependencies = ["massMailingSocialMediaOptionPlugin"];
    apply({ editingElement, params: { position } }) {
        if (this.isApplied(...arguments)) {
            return;
        }
        let titleEl = editingElement.querySelector(".s_social_media_title");
        if (!position) {
            titleEl?.remove();
        } else {
            if (!titleEl) {
                titleEl = this.dependencies.massMailingSocialMediaOptionPlugin.renderTitleEl();
                editingElement.prepend(titleEl);
            }
            titleEl.classList.toggle("d-block", position === "top");
        }
    }
    isApplied({ editingElement, params: { position } }) {
        const titleEl = editingElement.querySelector(".s_social_media_title");
        if (!position) {
            return !titleEl;
        } else if (!titleEl) {
            return false;
        } else {
            const hasDisplayBlock = titleEl.matches(".d-block");
            return position === "top" ? hasDisplayBlock : !hasDisplayBlock;
        }
    }
}

class ChangeCompanyAction extends BuilderAction {
    static id = "changeCompany";
    static dependencies = ["massMailingSocialMediaOptionPlugin"];
    async apply({ editingElement, params: company }) {
        if (this.isApplied(...arguments)) {
            return;
        }
        const baseMedias =
            await this.dependencies.massMailingSocialMediaOptionPlugin.fetchRecordedSocialMedia(
                company.id
            );
        const allLinks = [];
        for (const [platform, href] of Object.entries(baseMedias)) {
            const newLinkElement =
                this.dependencies.massMailingSocialMediaOptionPlugin.renderSocialMediaLink(
                    platform,
                    href
                );
            allLinks.push(newLinkElement);
        }
        editingElement.querySelector(LINKS_CONTAINER_SELECTOR).replaceChildren(...allLinks);
        editingElement.dataset.companyId = company.id;
    }
    isApplied({ editingElement, params: company }) {
        return parseInt(editingElement.dataset.companyId) === company.id;
    }
}

class ToggleSocialMediaLinkAction extends BuilderAction {
    static id = "toggleSocialMediaLink";
    static dependencies = ["builderActions", "massMailingSocialMediaOptionPlugin"];
    setup() {
        this.classAction = this.dependencies.builderActions.getAction("classAction");
        this.styleAction = this.dependencies.builderActions.getAction("styleAction");
    }

    apply({ editingElement, params: { platform, getIndex, href } }) {
        const editingLink = editingElement.querySelector(`[data-platform="${platform}"]`);
        if (editingLink) {
            editingLink.remove();
            return;
        }
        // Add a link
        if (href) {
            this.dependencies.massMailingSocialMediaOptionPlugin.addMedia(platform, href);
        } else {
            href = this.dependencies.massMailingSocialMediaOptionPlugin.getMedias()[platform];
        }
        const newLinkElement =
            this.dependencies.massMailingSocialMediaOptionPlugin.renderSocialMediaLink(
                platform,
                href
            );
        const index = getIndex();
        const sibling =
            index === 0
                ? editingElement.querySelector("[data-platform]:first-of-type")
                : editingElement.querySelector(`[data-platform]:nth-of-type(${index})`);
        if (index === 0) {
            sibling
                ? sibling.before(newLinkElement)
                : editingElement.querySelector(LINKS_CONTAINER_SELECTOR).prepend(newLinkElement);
        } else {
            sibling.after(newLinkElement);
        }
        const referenceIcon = sibling?.querySelector(".fa");
        if (referenceIcon) {
            const backgroundColor = this.styleAction.getValue({
                editingElement: referenceIcon,
                params: { mainParam: "background-color" },
            });
            const color = this.styleAction.getValue({
                editingElement: referenceIcon,
                params: { mainParam: "color" },
            });
            const appliedClasses = LINK_OPTIONS_CLASSLIST.filter((className) =>
                this.classAction.isApplied({
                    editingElement: referenceIcon,
                    params: { mainParam: className },
                })
            );
            const icon = newLinkElement.querySelector(".fa");
            if (backgroundColor) {
                icon.style.backgroundColor = backgroundColor;
            }
            if (color) {
                icon.style.color = color;
            }
            icon.classList.remove("fa-stack");
            icon.classList.add(...appliedClasses);
        }
    }
    isApplied({ editingElement, params }) {
        return editingElement.querySelector(`[data-platform="${params.platform}"]`) !== null;
    }
}

class RemoveCustomSocialMediaLinkAction extends BuilderAction {
    static id = "removeCustomMediaLink";
    apply({ editingElement, params: { platform } }) {
        const link = editingElement.querySelector(`[data-platform="${platform}"]`);
        link.remove();
    }
}

class AddSocialMediaLinkAction extends BuilderAction {
    static id = "addSocialMediaLink";
    static dependencies = ["clone", "massMailingSocialMediaOptionPlugin"];
    async apply({ editingElement }) {
        const elementToClone = editingElement.querySelector("[data-platform]:last-of-type");
        if (!elementToClone) {
            const element = renderToElement("mass_mailing.social_media_link", {
                href: "https://www.example.com",
                platform: uniqueId("customLink-"),
                icon: `fa-home`,
            });
            editingElement.querySelector(LINKS_CONTAINER_SELECTOR).append(element);
        } else {
            const cloneEl = await this.dependencies.clone.cloneElement(elementToClone, {
                position: "afterend",
                activateClone: false,
            });
            setAttributes(cloneEl, {
                href: "https://www.example.com",
                "data-platform": uniqueId("customLink-"),
            });
            const icon = cloneEl.querySelector(".fa");
            const faClassesToRemove = [...icon.classList].filter(
                (className) => className.startsWith("fa-") && className !== "fa-stack"
            );
            icon.classList.remove(...faClassesToRemove);
            icon.classList.add("fa-home");
        }
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingSocialMediaOptionPlugin.id, MassMailingSocialMediaOptionPlugin);
