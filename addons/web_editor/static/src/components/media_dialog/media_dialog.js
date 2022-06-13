/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { ImageSelector } from './image_selector';
import { DocumentSelector } from './document_selector';
import { IconSelector } from './icon_selector';
import { VideoSelector } from './video_selector';

const { useState } = owl;

export const TABS = {
    IMAGES: {
        id: 'IMAGES',
        title: "Images",
        Component: ImageSelector,
    },
    DOCUMENTS: {
        id: 'DOCUMENTS',
        title: "Documents",
        Component: DocumentSelector,
    },
    ICONS: {
        id: 'ICONS',
        title: "Icons",
        Component: IconSelector,
    },
    VIDEOS: {
        id: 'VIDEOS',
        title: "Videos",
        Component: VideoSelector,
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

        this.addTabs();

        this.state = useState({
            activeTab: this.initialActiveTab,
        });
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
                selectedMedia: this.selectedMedia,
                selectMedia: (...args) => this.selectMedia(...args, tab.id, additionalProps.multiSelect),
                save: this.save.bind(this),
            },
        });
    }

    addTabs() {
        const onlyImages = this.props.onlyImages || this.props.multiImages || (this.props.media && this.props.media.parentElement && (this.props.media.parentElement.dataset.oeField === 'image' || this.props.media.parentElement.dataset.oeType === 'image'));
        const noDocuments = onlyImages || this.props.noDocuments;
        const noIcons = onlyImages || this.props.noIcons;
        const noVideos = onlyImages || this.props.noVideos;

        if (!this.props.noImages) {
            this.addTab(TABS.IMAGES, {
                useMediaLibrary: this.props.useMediaLibrary,
                multiSelect: this.props.multiImages
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
        const selectedMedia = this.selectedMedia[this.state.activeTab];
        if (selectedMedia.length) {
            const elements = await TABS[this.state.activeTab].Component.createElements(selectedMedia);
            if (this.props.multiImages) {
                this.props.save(elements);
            } else {
                this.props.save(elements[0]);
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
