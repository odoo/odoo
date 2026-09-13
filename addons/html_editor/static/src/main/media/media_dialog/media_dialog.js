/** @odoo-module native */
import { iconClasses } from "@html_editor/utils/dom_info";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { Notebook } from "@web/components/notebook";
import { _t } from "@web/core/translation";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog";

import { IconSelector } from "./icon_selector.js";
import { ImageSelector } from "./image_selector.js";

export const TABS = {
    IMAGES: {
        id: "IMAGES",
        title: _t("Images"),
        Component: ImageSelector,
        sequence: 10,
    },
    ICONS: {
        id: "ICONS",
        title: _t("Icons"),
        Component: IconSelector,
        sequence: 20,
    },
};

const DEFAULT_SEQUENCE = 50;
const sequence = (tab) => tab.sequence ?? DEFAULT_SEQUENCE;

export class MediaDialog extends Component {
    static template = "html_editor.MediaDialog";
    static defaultProps = {
        useMediaLibrary: true,
        extraTabs: [],
    };
    static components = {
        Dialog,
        Notebook,
    };
    static props = {
        extraTabs: { type: Array, optional: true, element: Object },
        visibleTabs: { type: Array, optional: true, element: String },
        activeTab: { type: String, optional: true },
        "*": true,
    };

    setup() {
        this.size = "xl";
        this.contentClass = "o_select_media_dialog h-100";
        this.title = _t("Select a media");
        this.modalRef = useChildRef();

        this.orm = useService("orm");
        this.notificationService = useService("notification");

        this.selectedMedia = useState({});

        this.addButtonRef = useRef("add-button");

        this.initialIconClasses = [];

        this.notebookPages = [];
        this.addTabs();
        this.notebookPages.sort((a, b) => sequence(a) - sequence(b));
        this.tabs = Object.fromEntries(this.notebookPages.map((tab) => [tab.id, tab]));

        this.errorMessages = {};

        this.state = useState({
            activeTab: this.initialActiveTab,
            isSaving: false,
        });

        useEffect(
            (nbSelectedAttachments) => {
                this.addButtonRef.el.toggleAttribute(
                    "disabled",
                    !nbSelectedAttachments || this.state.isSaving,
                );
            },
            () => [
                this.selectedMedia[this.state.activeTab].length,
                this.state.isSaving,
            ],
        );
        this.abortUploads = null;
    }

    get initialActiveTab() {
        if (this.props.activeTab) {
            return this.props.activeTab;
        }
        if (this.props.media) {
            const correspondingTab =
                Object.keys(this.tabs).find((id) =>
                    this.tabs[id].Component.mediaSpecificClasses.some((cls) =>
                        [...this.props.media.classList].includes(cls),
                    ),
                ) ||
                Object.keys(this.tabs).find((id) =>
                    this.tabs[id].Component.tagNames.includes(this.props.media.tagName),
                );
            if (correspondingTab) {
                return correspondingTab;
            }
        }
        return this.notebookPages[0].id;
    }

    addTab(tab, additionalProps = {}) {
        if (this.props.visibleTabs && !this.props.visibleTabs.includes(tab.id)) {
            return;
        }
        this.selectedMedia[tab.id] = [];
        this.notebookPages.push({
            ...tab,
            props: {
                ...tab.props,
                ...additionalProps,
                id: tab.id,
                resModel: this.props.resModel,
                resId: this.props.resId,
                media: this.props.media,
                selectedMedia: this.selectedMedia,
                selectMedia: (...args) =>
                    this.selectMedia(...args, tab.id, additionalProps.multiSelect),
                save: this.save.bind(this),
                setAbortUploadsCallback: (abortFunc) => (this.abortUploads = abortFunc),
                onAttachmentChange: this.props.onAttachmentChange,
                errorMessages: (errorMessage) =>
                    (this.errorMessages[tab.id] = errorMessage),
                modalRef: this.modalRef,
            },
        });
    }

    addTabs() {
        const onlyImages =
            this.props.onlyImages ||
            (this.props.media &&
                this.props.media.parentElement &&
                (this.props.media.parentElement.dataset.oeField === "image" ||
                    this.props.media.parentElement.dataset.oeType === "image"));

        if (!this.props.noImages) {
            this.addTab(TABS.IMAGES, {
                useMediaLibrary: this.props.useMediaLibrary,
                multiSelect: this.props.multiImages,
                addFieldImage: this.props.addFieldImage,
            });
        }
        if (onlyImages) {
            return;
        }
        const addIcons =
            !this.props.visibleTabs || this.props.visibleTabs.includes(TABS.ICONS.id);
        if (addIcons) {
            const fonts = TABS.ICONS.Component.initFonts();
            this.addTab(TABS.ICONS, {
                fonts,
            });

            if (
                this.props.media &&
                TABS.ICONS.Component.tagNames.includes(this.props.media.tagName)
            ) {
                const classes = this.props.media.className.split(/\s+/);
                // the media's own face first: a few names exist in two faces
                const byAffinity = [...fonts].sort(
                    (a, b) => classes.includes(b.base) - classes.includes(a.base),
                );
                let selectedIcon;
                for (const font of byAffinity) {
                    selectedIcon = font.icons.find((icon) =>
                        icon.names.some((name) => classes.includes(name)),
                    );
                    if (selectedIcon) {
                        selectedIcon = { ...selectedIcon, fontBase: font.base };
                        break;
                    }
                }
                if (selectedIcon) {
                    this.initialIconClasses.push(...selectedIcon.names);
                    this.selectMedia(selectedIcon, TABS.ICONS.id);
                } else {
                    const iconRegex = new RegExp(
                        `\\b(?:${iconClasses.join("|")})(?:-\\S+)?\\b`,
                    );
                    const fallbackIconClasses = classes.filter((cls) =>
                        iconRegex.test(cls),
                    );
                    this.initialIconClasses.push(...fallbackIconClasses);
                }
            }
        }
        this.props.extraTabs.forEach((tab) => this.addTab(tab));
    }

    /**
     * @param {Array<Object>} selectedMedia
     * @returns {Array<HTMLElement>}
     */
    async renderMedia(selectedMedia) {
        const ActiveComponent = this.tabs[this.state.activeTab].Component;
        const elements = await ActiveComponent.createElements(selectedMedia, {
            orm: this.orm,
        });
        elements.forEach((element, index) => {
            if (this.props.media) {
                element.classList.add(...this.props.media.classList);
                const style = this.props.media.getAttribute("style");
                if (style) {
                    element.setAttribute("style", style);
                }
            }
            for (const otherTab of Object.keys(this.tabs).filter(
                (key) => key !== this.state.activeTab,
            )) {
                for (const property of this.tabs[otherTab].Component
                    .mediaSpecificStyles) {
                    element.style.removeProperty(property);
                }
                element.classList.remove(
                    ...this.tabs[otherTab].Component.mediaSpecificClasses,
                );
                const extraClassesToRemove = [];
                for (const name of this.tabs[otherTab].Component.mediaExtraClasses) {
                    if (typeof name === "string") {
                        extraClassesToRemove.push(name);
                    } else {
                        for (const className of element.classList) {
                            if (className.match(name)) {
                                extraClassesToRemove.push(className);
                            }
                        }
                    }
                }
                element.classList.remove(
                    ...extraClassesToRemove.filter((candidateName) => {
                        for (const name of this.tabs[this.state.activeTab].Component
                            .mediaExtraClasses) {
                            if (typeof name === "string") {
                                if (candidateName === name) {
                                    return false;
                                }
                            } else {
                                if (candidateName.match(name)) {
                                    return false;
                                }
                            }
                        }
                        return true;
                    }),
                );
            }
            element.classList.remove(...this.initialIconClasses);
            element.classList.remove("o_modified_image_to_save");
            element.classList.remove("oe_edited_link");
            // a tab may own several classes but stamp only some on a given
            // media (an icon font renders in exactly one face)
            const specificClasses =
                ActiveComponent.getMediaSpecificClasses?.(selectedMedia[index]) ??
                ActiveComponent.mediaSpecificClasses;
            element.classList.remove(
                ...ActiveComponent.mediaSpecificClasses.filter(
                    (cls) => !specificClasses.includes(cls),
                ),
            );
            element.classList.add(...specificClasses);
        });
        return elements;
    }

    selectMedia(media, tabId, multiSelect) {
        if (media && !Object.keys(media).length) {
            this.selectedMedia[tabId] = [];
            return;
        }
        if (multiSelect) {
            const isMediaSelected = this.selectedMedia[tabId]
                .map(({ id }) => id)
                .includes(media.id);
            if (!isMediaSelected) {
                this.selectedMedia[tabId].push(media);
            } else {
                this.selectedMedia[tabId] = this.selectedMedia[tabId].filter(
                    (m) => m.id !== media.id,
                );
            }
        } else {
            this.selectedMedia[tabId] = [media];
        }
    }

    async save() {
        if (this.errorMessages[this.state.activeTab]) {
            this.notificationService.add(this.errorMessages[this.state.activeTab], {
                type: "danger",
            });
            return;
        }
        const selectedMedia = this.selectedMedia[this.state.activeTab];
        const saveSelectedMedia =
            selectedMedia.length &&
            (this.state.activeTab !== TABS.ICONS.id ||
                selectedMedia[0].initialIconChanged ||
                !this.props.media);
        this.state.isSaving = true;
        if (saveSelectedMedia) {
            const elements = await this.renderMedia(selectedMedia);
            if (this.props.multiImages) {
                await this.props.save(elements, selectedMedia, this.state.activeTab);
            } else {
                await this.props.save(elements[0], selectedMedia, this.state.activeTab);
            }
        }
        this.props.close();
        this.state.isSaving = false;
    }

    onTabChange(tab) {
        this.state.activeTab = tab;
    }
    async close() {
        if (this.abortUploads) {
            this.abortUploads();
            delete this.abortUploads;
        }
        this.state.isSaving = false;
        await this.props.close();
    }
}
