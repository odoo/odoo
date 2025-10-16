import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onWillStart, useRef } from "@odoo/owl";
import { useSortable } from "@web/core/utils/sortable_owl";
import { user } from "@web/core/user";
import { ResCompanyUpdateDialog } from "../components/company_update_dialog";

export class SocialMediaLinks extends BaseOptionComponent {
    static template = "mass_mailing.SocialMediaLinks";
    static dependencies = ["builderActions", "history", "massMailingSocialMediaOptionPlugin"];
    static name = "social_media_links";
    static selector = ".s_social_media";

    /** @override */
    setup() {
        super.setup();
        this.companies = user.allowedCompanies;
        this.overlayButtonsPlugin = this.env.editor.shared.overlayButtons;
        this.rootRef = useRef("root");

        onWillStart(async () => {
            this.canEditCompanies = await user.checkAccessRight("res.company", "write");
        });

        this.domState = useDomState((editingElement) => {
            const orderedMediaEntries = [];
            for (const el of editingElement.querySelectorAll("a[data-platform]")) {
                const media = {
                    href: el.href,
                    active: true,
                    custom:
                        el.dataset.platform.includes("customLink-") ||
                        !this.baseMedias[el.dataset.platform],
                };
                orderedMediaEntries.push([el.dataset.platform, media]);
            }
            const shownMedias = Object.fromEntries(orderedMediaEntries);
            if (
                this.domState.medias?.length &&
                this.domState.companyId === editingElement.dataset.companyId
            ) {
                const activeMediaEntries = [];
                const inactiveMediaEntries = [];
                let medias = this.domState.medias.filter(([platform, mediaInfo]) => {
                    mediaInfo.active = !!shownMedias[platform];
                    if (!mediaInfo.active && mediaInfo.custom) {
                        return false;
                    } else if (mediaInfo.active) {
                        delete shownMedias[platform];
                        activeMediaEntries.push([platform, mediaInfo]);
                    } else {
                        inactiveMediaEntries.push([platform, mediaInfo]);
                    }
                    return true;
                });
                for (const [newPlatform, mediaInfo] of Object.entries(shownMedias)) {
                    const mediaEntry = [newPlatform, mediaInfo];
                    medias.push(mediaEntry);
                    activeMediaEntries.push(mediaEntry);
                }
                if (
                    orderedMediaEntries.some(
                        ([platform], index) => platform !== activeMediaEntries[index][0]
                    )
                ) {
                    medias = orderedMediaEntries.concat(inactiveMediaEntries);
                }
                return { medias };
            }
            const inactiveMediaEntries = [];
            for (const platform in this.baseMedias) {
                if (!shownMedias[platform]) {
                    inactiveMediaEntries.push([
                        platform,
                        { href: this.baseMedias[platform], active: false },
                    ]);
                }
            }
            return {
                medias: orderedMediaEntries.concat(inactiveMediaEntries),
                companyId: editingElement.dataset.companyId,
            };
        });
        useSortable({
            ref: this.rootRef,
            elements: ".hb-row",
            handle: ".o_drag_handle",
            cursor: "grabbing",
            placeholderClasses: ["d-table-row"],
            onDrop: ({ next, element }) => {
                let nextPlatform = next?.querySelector("[data-sortable-platform]")?.dataset
                    .sortablePlatform;
                const elementPlatform = element.querySelector("[data-sortable-platform]").dataset
                    .sortablePlatform;
                const index = this.getIndex(elementPlatform, false);
                const [media] = this.domState.medias.splice(index, 1);
                let nextIndex = this.getIndex(nextPlatform, false);
                this.domState.medias.splice(nextIndex, 0, media);
                if (!media[1].active && !media[1].custom) {
                    return;
                }

                if (!this.domState.medias.at(++nextIndex)?.[1].active) {
                    do {
                        ++nextIndex;
                    } while (
                        this.domState.medias[nextIndex] &&
                        !this.domState.medias[nextIndex]?.[1].active
                    );
                    nextPlatform = this.domState.medias.at(nextIndex)?.[0];
                }

                this.dependencies.massMailingSocialMediaOptionPlugin.reorderSocialMediaLinks({
                    editingElement: this.env.getEditingElement(),
                    platform: elementPlatform,
                    platformAfter: nextPlatform,
                });
            },
        });
    }

    updateCompany() {
        const companyId = parseInt(this.domState.companyId);
        if (!companyId) {
            return;
        }
        const fields = this.baseMedias;
        const mappedFields = {};
        for (const field in fields) {
            mappedFields[`social_${field}`] = fields[field];
        }
        this.overlayButtonsPlugin.hideOverlayButtonsUi();
        this.services.dialog.add(
            ResCompanyUpdateDialog,
            {
                resId: companyId,
                onRecordSaved: (state) => {
                    const editingElement = this.env.getEditingElement();
                    const platformLinks = editingElement.querySelectorAll(
                        "[data-platform]:not([data-platform*=customLink-])"
                    );
                    const medias = this.medias;
                    platformLinks.forEach((link) => {
                        const platform = link.dataset.platform;
                        if (state[platform]) {
                            link.setAttribute("href", state[platform]);
                        } else if (state[platform] === "") {
                            link.dataset.platform = `customLink-${platform}`;
                            this.dependencies.massMailingSocialMediaOptionPlugin.removeMedia(
                                platform
                            );
                            delete medias[platform];
                        }
                        delete state[platform];
                    });
                    for (const [platform, href] of Object.entries(state)) {
                        if (medias[platform]) {
                            if (href) {
                                this.dependencies.massMailingSocialMediaOptionPlugin.addMedia(
                                    platform,
                                    href
                                );
                                medias[platform].href = href;
                            } else {
                                delete medias[platform];
                            }
                        } else if (href) {
                            this.dependencies.builderActions
                                .getAction("toggleSocialMediaLink")
                                .apply({
                                    editingElement,
                                    params: {
                                        href,
                                        platform,
                                        getIndex: () =>
                                            editingElement
                                                .querySelector(".s_social_media_links")
                                                .querySelectorAll("[data-platform]").length,
                                    },
                                });
                            medias[platform] = { href, active: true, custom: false };
                        }
                    }
                    this.domState.medias = Object.entries(medias);
                    this.dependencies.history.addStep();
                },
            },
            {
                onClose: () => {
                    this.overlayButtonsPlugin.showOverlayButtonsUi();
                },
            }
        );
    }

    get medias() {
        return Object.fromEntries(this.domState.medias);
    }

    getIndex(platform, returnLastActiveIndex = true) {
        if (!platform) {
            return this.domState.medias.length;
        }
        const allMedias = this.domState.medias;
        let lastActiveMediaIndex = 0;
        const index = allMedias.findIndex(([mediaPlatform, mediaInfo]) => {
            if (mediaInfo.active || mediaInfo.custom) {
                lastActiveMediaIndex++;
            }
            return mediaPlatform === platform;
        });
        if (index < 0 || !returnLastActiveIndex) {
            return index;
        }
        const mediaInfo = allMedias.at(index)[1];
        return mediaInfo.active || mediaInfo.custom ? index : lastActiveMediaIndex;
    }

    get baseMedias() {
        return this.dependencies["massMailingSocialMediaOptionPlugin"].getMedias();
    }
}
