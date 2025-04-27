import { _t } from "@web/core/l10n/translation";
import { useService, useChildRef } from '@web/core/utils/hooks';
import { Mutex } from "@web/core/utils/concurrency";
import { Dialog } from '@web/core/dialog/dialog';
import { Notebook } from '@web/core/notebook/notebook';
import { ImageSelector } from './image_selector';
import { DocumentSelector } from './document_selector';
import { IconSelector } from './icon_selector';
import { VideoSelector } from './video_selector';
import { WordartSelector } from './wordart_selector';

import { Component, useState, useRef, useEffect } from "@odoo/owl";

export const TABS = {
    IMAGES: {
        id: 'IMAGES',
        title: _t("Images"),
        Component: ImageSelector,
    },
    DOCUMENTS: {
        id: 'DOCUMENTS',
        title: _t("Documents"),
        Component: DocumentSelector,
    },
    ICONS: {
        id: 'ICONS',
        title: _t("Icons"),
        Component: IconSelector,
    },
    VIDEOS: {
        id: 'VIDEOS',
        title: _t("Videos"),
        Component: VideoSelector,
    },
    WORDART: {
        id: 'WORDART',
        title: "Wordart",
        Component: WordartSelector,
    },
};

export class MediaDialog extends Component {
    static template = "web_editor.MediaDialog";
    static defaultProps = {
        useMediaLibrary: true,
    };
    static components = {
        ...Object.keys(TABS).map((key) => TABS[key].Component),
        Dialog,
        Notebook,
    };
    static props = ["*"];

    setup() {
        this.size = 'xl';
        this.contentClass = 'o_select_media_dialog h-100';
        this.modalRef = useChildRef();

        this.orm = useService('orm');
        this.notificationService = useService('notification');
        this.mutex = new Mutex();

        this.tabs = [];
        this.selectedMedia = useState({});

        this.addButtonRef = useRef('add-button');

        this.initialIconClasses = [];

        this.addTabs();
        this.errorMessages = {};

        this.state = useState({
            activeTab: this.initialActiveTab,
        });

        useEffect(
            (nbSelectedAttachments) => {
                // Disable/enable the add button depending on whether some media
                // are selected or not.
                this.addButtonRef.el.toggleAttribute("disabled", !nbSelectedAttachments);
            },
            () => [this.selectedMedia[this.state.activeTab].length]
        );
    }

    get initialActiveTab() {
        if (this.props.activeTab) {
            return this.props.activeTab;
        }
        if (this.props.media) {
            const correspondingTab = Object.keys(TABS).find(id => TABS[id].Component.tagNames.includes(this.props.media.tagName));
            if (correspondingTab) {
                return correspondingTab;
            }
        }
        return this.tabs[0].id;
    }

    addTab(tab, additionalProps = {}) {
        this.selectedMedia[tab.id] = [];
        this.tabs.push({
            ...tab,
            props: {
                ...tab.props,
                ...additionalProps,
                id: tab.id,
                resModel: this.props.resModel,
                resId: this.props.resId,
                media: this.props.media,
                multiImages: this.props.multiImages,
                selectedMedia: this.selectedMedia,
                selectMedia: (...args) => this.selectMedia(...args, tab.id, additionalProps.multiSelect),
                save: this.save.bind(this),
                onAttachmentChange: this.props.onAttachmentChange,
                errorMessages: (errorMessage) => this.errorMessages[tab.id] = errorMessage,
                modalRef: this.modalRef,
            },
        });
    }

    addTabs() {
        const onlyImages = this.props.onlyImages || (this.props.media && this.props.media.parentElement && (this.props.media.parentElement.dataset.oeField === 'image' || this.props.media.parentElement.dataset.oeType === 'image'));
        const noDocuments = onlyImages || this.props.noDocuments;
        const noIcons = onlyImages || this.props.noIcons;
        const noVideos = onlyImages || this.props.noVideos;
        const noWordart = onlyImages;

        if (!this.props.noImages) {
            this.addTab(TABS.IMAGES, {
                useMediaLibrary: this.props.useMediaLibrary,
                multiSelect: this.props.multiImages,
            });
        }
        if (!noDocuments) {
            this.addTab(TABS.DOCUMENTS);
        }
        if (!noIcons) {
            const fonts = TABS.ICONS.Component.initFonts();
            this.addTab(TABS.ICONS, {
                fonts,
            });

            if (this.props.media && TABS.ICONS.Component.tagNames.includes(this.props.media.tagName)) {
                const classes = this.props.media.className.split(/\s+/);
                const mediaFont = fonts.find(font => classes.includes(font.base));
                if (mediaFont) {
                    const selectedIcon = mediaFont.icons.find(icon => icon.names.some(name => classes.includes(name)));
                    if (selectedIcon) {
                        this.initialIconClasses.push(...selectedIcon.names);
                        this.selectMedia(selectedIcon, TABS.ICONS.id);
                    }
                }
            }
        }
        if (!noVideos) {
            this.addTab(TABS.VIDEOS, {
                vimeoPreviewIds: this.props.vimeoPreviewIds,
                isForBgVideo: this.props.isForBgVideo,
            });
        }
        if (!noWordart) {
            this.addTab(TABS.WORDART, {
                // TODO Obtain fonts ?
            });
        }
    }

    /**
     * Render the selected media for insertion in the editor
     *
     * @param {Array<Object>} selectedMedia
     * @returns {Array<HTMLElement>}
     */
    async renderMedia(selectedMedia) {
        // Calling a mutex to make sure RPC calls inside `createElements` are
        // properly awaited (e.g. avoid creating multiple attachments when
        // clicking multiple times on the same media). As `createElements` is
        // static, the mutex has to be set on the media dialog itself to be
        // destroyed with its instance.
        const elements = await this.mutex.exec(async() =>
            await TABS[this.state.activeTab].Component.createElements(selectedMedia, { orm: this.orm })
        );
        elements.forEach(element => {
            if (this.props.media) {
                element.classList.add(...this.props.media.classList);
                const style = this.props.media.getAttribute('style');
                if (style) {
                    element.setAttribute('style', style);
                }
                if (this.state.activeTab === TABS.IMAGES.id) {
                    if (this.props.media.dataset.shape) {
                        element.dataset.shape = this.props.media.dataset.shape;
                    }
                    if (this.props.media.dataset.shapeColors) {
                        element.dataset.shapeColors = this.props.media.dataset.shapeColors;
                    }
                    if (this.props.media.dataset.shapeFlip) {
                        element.dataset.shapeFlip = this.props.media.dataset.shapeFlip;
                    }
                    if (this.props.media.dataset.shapeRotate) {
                        element.dataset.shapeRotate = this.props.media.dataset.shapeRotate;
                    }
                    if (this.props.media.dataset.hoverEffect) {
                        element.dataset.hoverEffect = this.props.media.dataset.hoverEffect;
                    }
                    if (this.props.media.dataset.hoverEffectColor) {
                        element.dataset.hoverEffectColor = this.props.media.dataset.hoverEffectColor;
                    }
                    if (this.props.media.dataset.hoverEffectStrokeWidth) {
                        element.dataset.hoverEffectStrokeWidth = this.props.media.dataset.hoverEffectStrokeWidth;
                    }
                    if (this.props.media.dataset.hoverEffectIntensity) {
                        element.dataset.hoverEffectIntensity = this.props.media.dataset.hoverEffectIntensity;
                    }
                    if (this.props.media.dataset.shapeAnimationSpeed) {
                        element.dataset.shapeAnimationSpeed = this.props.media.dataset.shapeAnimationSpeed;
                    }
                } else if ([TABS.VIDEOS.id, TABS.DOCUMENTS.id].includes(this.state.activeTab)) {
                    const parentEl = this.props.media.parentElement;
                    if (
                        parentEl &&
                        parentEl.tagName === "A" &&
                        parentEl.children.length === 1 &&
                        this.props.media.tagName === "IMG"
                    ) {
                        // If an image is wrapped in an <a> tag, we remove the link when replacing it with a video or document
                        parentEl.replaceWith(parentEl.firstElementChild);
                    }
                }
            }
            for (const otherTab of Object.keys(TABS).filter(key => key !== this.state.activeTab)) {
                for (const property of TABS[otherTab].Component.mediaSpecificStyles) {
                    element.style.removeProperty(property);
                }
                element.classList.remove(...TABS[otherTab].Component.mediaSpecificClasses);
                const extraClassesToRemove = [];
                for (const name of TABS[otherTab].Component.mediaExtraClasses) {
                    if (typeof(name) === 'string') {
                        extraClassesToRemove.push(name);
                    } else { // Regex
                        for (const className of element.classList) {
                            if (className.match(name)) {
                                extraClassesToRemove.push(className);
                            }
                        }
                    }
                }
                // Remove classes that do not also exist in the target type.
                element.classList.remove(...extraClassesToRemove.filter(candidateName => {
                    for (const name of TABS[this.state.activeTab].Component.mediaExtraClasses) {
                        if (typeof(name) === 'string') {
                            if (candidateName === name) {
                                return false;
                            }
                        } else { // Regex
                            for (const className of element.classList) {
                                if (className.match(candidateName)) {
                                    return false;
                                }
                            }
                        }
                    }
                    return true;
                }));
            }
            element.classList.remove(...this.initialIconClasses);
            element.classList.remove('o_modified_image_to_save');
            element.classList.remove('oe_edited_link');
            element.classList.add(...TABS[this.state.activeTab].Component.mediaSpecificClasses);
        });
        return elements;
    }

    selectMedia(media, tabId, multiSelect) {
        if (multiSelect) {
            const isMediaSelected = this.selectedMedia[tabId].map(({ id }) => id).includes(media.id);
            if (!isMediaSelected) {
                this.selectedMedia[tabId].push(media);
            } else {
                this.selectedMedia[tabId] = this.selectedMedia[tabId].filter(m => m.id !== media.id);
            }
        } else {
            this.selectedMedia[tabId] = [media];
        }
    }

    async save() {
        if (this.errorMessages[this.state.activeTab]) {
            this.notificationService.add(this.errorMessages[this.state.activeTab], {
                type: 'danger',
            });
            return;
        }
        const selectedMedia = this.selectedMedia[this.state.activeTab];
        // TODO In master: clean the save method so it performs the specific
        // adaptation before saving from the active media selector and find a
        // way to simply close the dialog if the media element remains the same.
        const saveSelectedMedia = selectedMedia.length
            && (this.state.activeTab !== TABS.ICONS.id || selectedMedia[0].initialIconChanged || !this.props.media);
        if (saveSelectedMedia) {
            const elements = await this.renderMedia(selectedMedia);
            if (this.props.multiImages) {
                await this.props.save(elements);
            } else {
                await this.props.save(elements[0]);
            }
        }
        this.props.close();
    }

    onTabChange(tab) {
        this.state.activeTab = tab;
    }
}
