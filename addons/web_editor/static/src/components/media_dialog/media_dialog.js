/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { useWowlService } from '@web/legacy/utils';
import { Dialog } from '@web/core/dialog/dialog';
import { ImageSelector, saveImages, imageTagNames, imageSpecificClasses } from './image_selector';
import { DocumentSelector, saveDocuments, documentTagNames, documentSpecificClasses } from './document_selector';
import { IconSelector, saveIcons, iconTagNames, iconSpecificClasses } from './icon_selector';
import { VideoSelector, saveVideos, videoTagNames, videoSpecificClasses } from './video_selector';

const { Component, useState, useEffect, xml } = owl;

export const TABS = {
    IMAGES: {
        id: 'IMAGES',
        title: "Images",
        Component: ImageSelector,
        save: saveImages,
        mediaSpecificClasses: imageSpecificClasses,
        tagNames: imageTagNames,
    },
    DOCUMENTS: {
        id: 'DOCUMENTS',
        title: "Documents",
        Component: DocumentSelector,
        save: saveDocuments,
        mediaSpecificClasses: documentSpecificClasses,
        tagNames: documentTagNames,
    },
    ICONS: {
        id: 'ICONS',
        title: "Icons",
        Component: IconSelector,
        save: saveIcons,
        mediaSpecificClasses: iconSpecificClasses,
        tagNames: iconTagNames,
    },
    VIDEOS: {
        id: 'VIDEOS',
        title: "Videos",
        Component: VideoSelector,
        save: saveVideos,
        mediaSpecificClasses: videoSpecificClasses,
        tagNames: videoTagNames,
    },
};

export class MediaDialog extends Dialog {
    setup() {
        super.setup();
        this.size = 'modal-xl';
        this.contentClass = 'o_select_media_dialog';
        this.title = this.env._t("Select a media");

        this.rpc = useService('rpc');
        this.orm = useService('orm');

        this.tabs = [];
        this.selectedMedia = useState({});

        const onlyImages = this.props.onlyImages || this.props.multiImages || (this.props.media && this.props.media.parentElement && (this.props.media.parentElement.dataset.oeField === 'image' || this.props.media.parentElement.dataset.oeType === 'image'));
        const noDocuments = onlyImages || this.props.noDocuments;
        const noIcons = onlyImages || this.props.noIcons;
        const noVideos = onlyImages || this.props.noVideos;

        this.initialIconClasses = [];

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
            this.addTab(TABS.ICONS, {
                setInitialIconClasses: (classes) => this.initialIconClasses.push(...classes),
            });
        }
        if (!noVideos) {
            this.addTab(TABS.VIDEOS, {
                vimeoPreviewIds: this.props.vimeoPreviewIds,
                isForBgVideo: this.props.isForBgVideo,
            });
        }

        this.state = useState({
            activeTab: this.initialActiveTab,
        });
    }

    get initialActiveTab() {
        if (this.props.activeTab) {
            return this.props.activeTab;
        }
        if (this.props.media) {
            const correspondingTab = Object.keys(TABS).filter(id => TABS[id].tagNames.includes(this.props.media.tagName))[0];
            if (correspondingTab) {
                return correspondingTab;
            }
        }
        return this.tabs[0].id;
    }

    addTab(tab, props) {
        this.selectedMedia[tab.id] = [];
        this.tabs.push({
            ...tab,
            props: {
                ...tab.props,
                ...props,
                id: tab.id,
                resModel: this.props.resModel,
                resId: this.props.resId,
                media: this.props.media,
                multiImages: this.props.multiImages,
                selectedMedia: this.selectedMedia,
                selectMedia: async (media, { multiSelect = false, save = true } = {}) => {
                    if (multiSelect) {
                        const isMediaSelected = this.selectedMedia[tab.id].map(({ id }) => id).includes(media.id);
                        if (!isMediaSelected) {
                            this.selectedMedia[tab.id].push(media);
                        } else {
                            this.selectedMedia[tab.id] = this.selectedMedia[tab.id].filter(m => m.id !== media.id);
                        }
                    } else {
                        this.selectedMedia[tab.id] = [media];
                        if (save) {
                            await this.save();
                        }
                    }
                },
            },
        });
    }

    async save() {
        const selectedMedia = this.selectedMedia[this.state.activeTab];
        if (selectedMedia.length) {
            const savedMedia = await TABS[this.state.activeTab].save(selectedMedia, { rpc: this.rpc, orm: this.orm });
            savedMedia.forEach(media => {
                if (this.props.media) {
                    media.classList.add(...this.props.media.classList);
                    const style = this.props.media.getAttribute('style');
                    if (style) {
                        media.setAttribute('style', style);
                    }
                    if (this.props.media.dataset.shape) {
                        media.dataset.shape = this.props.media.dataset.shape;
                    }
                    if (this.props.media.dataset.shapeColors) {
                        media.dataset.shapeColors = this.props.media.dataset.shapeColors;
                    }
                }
                media.classList.add(...TABS[this.state.activeTab].mediaSpecificClasses);
                for (const otherTab of Object.keys(TABS).filter(key => key !== this.state.activeTab)) {
                    media.classList.remove(...TABS[otherTab].mediaSpecificClasses);
                }
                media.classList.remove(...this.initialIconClasses);
                media.classList.remove('o_modified_image_to_save');
                media.classList.remove('oe_edited_link');
            });
            if (this.props.multiImages) {
                this.props.save(savedMedia);
            } else {
                this.props.save(savedMedia[0]);
            }
        }
        this.close();
    }
}
MediaDialog.bodyTemplate = 'web_editor.MediaDialogBody';
MediaDialog.footerTemplate = 'web_editor.MediaDialogFooter';
MediaDialog.components = {
    ...Object.keys(TABS).map(key => TABS[key].Component),
};

export class MediaDialogWrapper extends Component {
    setup() {
        this.dialogs = useWowlService('dialog');

        useEffect(() => {
            this.dialogs.add(MediaDialog, {
                ...this.props,
                close: () => {
                    if (this.props.close) {
                        this.props.close();
                    }
                    this.destroy();

                },
            });
        }, () => []);
    }
}
MediaDialogWrapper.template = xml``;
