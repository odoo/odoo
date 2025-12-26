import { _t } from "@web/core/l10n/translation";
import { useService, useChildRef } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Notebook } from "@web/core/notebook/notebook";

import { Component, useState, useRef, useEffect } from "@odoo/owl";
import { iconClasses } from "@html_editor/utils/dom_info";
import { TABS, renderAndSaveMedia } from "./media_dialog_utils"

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
                // Disable/enable the add button depending on whether some media
                // are selected or not.
                this.addButtonRef.el.toggleAttribute(
                    "disabled",
                    !nbSelectedAttachments || this.state.isSaving
                );
            },
            () => [this.selectedMedia[this.state.activeTab].length, this.state.isSaving]
        );
    }

    get initialActiveTab() {
        if (this.props.activeTab) {
            return this.props.activeTab;
        }
        if (this.props.media) {
            const correspondingTab = Object.keys(this.tabs).find((id) =>
                this.tabs[id].Component.tagNames.includes(this.props.media.tagName)
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
                // multiImages: this.props.multiImages,
                selectedMedia: this.selectedMedia,
                selectMedia: (...args) =>
                    this.selectMedia(...args, tab.id, additionalProps.multiSelect),
                save: this.save.bind(this),
                onAttachmentChange: this.props.onAttachmentChange,
                errorMessages: (errorMessage) => (this.errorMessages[tab.id] = errorMessage),
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
        const addIcons = !this.props.visibleTabs || this.props.visibleTabs.includes(TABS.ICONS.id);
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
                const predefinedMediaFont = fonts.find((font) => classes.includes(font.base));
                if (predefinedMediaFont) {
                    const selectedIcon = predefinedMediaFont.icons.find((icon) =>
                        icon.names.some((name) => classes.includes(name))
                    );
                    if (selectedIcon) {
                        this.initialIconClasses.push(...selectedIcon.names);
                        this.selectMedia(selectedIcon, TABS.ICONS.id);
                    }
                } else {
                    const iconRegex = new RegExp(`\\b(?:${iconClasses.join("|")})(?:-\\S+)?\\b`);
                    const fallbackIconClasses = classes.filter((cls) => iconRegex.test(cls));
                    this.initialIconClasses.push(...fallbackIconClasses);
                }
            }
        }
        this.props.extraTabs.forEach((tab) => this.addTab(tab));
    }

    extraClassesToAdd() {
        return [];
    }

    selectMedia(media, tabId, multiSelect) {
        if (media && !Object.keys(media).length) {
            // Clear media selection when an empty object is passed
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
                    (m) => m.id !== media.id
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
        // TODO In master: clean the save method so it performs the specific
        // adaptation before saving from the active media selector and find a
        // way to simply close the dialog if the media element remains the same.
        const saveSelectedMedia =
            selectedMedia.length &&
            (this.state.activeTab !== TABS.ICONS.id ||
                selectedMedia[0].initialIconChanged ||
                !this.props.media);
        this.state.isSaving = true;
        if (saveSelectedMedia) {
            await renderAndSaveMedia({
                orm: this.orm,
                activeTab: this.state.activeTab,
                availableTabs: this.tabs,
                oldMediaNode: this.props.media,
                selectedMedia: selectedMedia,
                extraClassesToAdd: this.extraClassesToAdd(),
                extraClassesToRemove: this.initialIconClasses,
                multiImages: this.props.multiImages,
                saveFunction: this.props.save,
            });
        }
        this.props.close();
        this.state.isSaving = false;
    }

    onTabChange(tab) {
        this.state.activeTab = tab;
    }
}
