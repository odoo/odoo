/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { qweb } from 'web.core';
import { Dialog } from '@web/core/dialog/dialog';
import { getCSSVariableValue } from 'web_editor.utils';
import { ImageSelector } from './image_selector';
import { DocumentSelector } from './document_selector';
import { IconSelector } from './icon_selector';
import { VideoSelector } from './video_selector';

const { useState } = owl;

const TABS = {
    IMAGES: {
        id: 'IMAGES',
        title: "Images",
        Component: ImageSelector,
        save: async (selectedMedia, { rpc, orm }) => {
            // Create all media-library attachments.
            const toSave = Object.fromEntries(selectedMedia.filter(media => media.mediaType === 'libraryMedia').map(media => [
                media.id, {
                    query: media.query || '',
                    is_dynamic_svg: !!media.isDynamicSVG,
                    dynamic_colors: media.dynamicColors,
                }
            ]));
            let savedMedia = [];
            if (Object.keys(toSave).length !== 0) {
                savedMedia = await rpc('/web_editor/save_library_media', { media: toSave });
            }
            const selected = selectedMedia.filter(media => media.mediaType === 'attachment').concat(savedMedia).map(attachment => {
                // Color-customize dynamic SVGs with the theme colors
                if (attachment.image_src && attachment.image_src.startsWith('/web_editor/shape/')) {
                    const colorCustomizedURL = new URL(attachment.image_src, window.location.origin);
                    colorCustomizedURL.searchParams.forEach((value, key) => {
                        const match = key.match(/^c([1-5])$/);
                        if (match) {
                            colorCustomizedURL.searchParams.set(key, getCSSVariableValue(`o-color-${match[1]}`));
                        }
                    });
                    attachment.image_src = colorCustomizedURL.pathname + colorCustomizedURL.search;
                }
                return attachment;
            });
            return Promise.all(selected.map(async (attachment) => {
                const imageEl = document.createElement('img');
                let src = attachment.image_src;
                if (!attachment.public) {
                    const [accessToken] = await orm.call(
                        'ir.attachment',
                        'generate_access_token',
                        [attachment.id],
                    );
                    src += `?access_token=${accessToken}`;
                }
                imageEl.src = src;
                imageEl.classList.add('img-fluid', 'o_we_custom_image');
                return imageEl;
            }));
        },
    },
    DOCUMENTS: {
        id: 'DOCUMENTS',
        title: "Documents",
        Component: DocumentSelector,
        save: (selectedMedia, { orm }) => {
            return Promise.all(selectedMedia.map(async attachment => {
                const linkEl = document.createElement('a');
                let href = `/web/content/${attachment.id}?unique=${attachment.checksum}&dowload=true`;
                if (!attachment.public) {
                    const [accessToken] = await orm.call(
                        'ir.attachment',
                        'generate_access_token',
                        [attachment.id],
                    );
                    href += `&access_token=${accessToken}`;
                }
                linkEl.href = href;
                linkEl.title = attachment.name;
                linkEl.dataset.mimetype = attachment.mimetype;
                linkEl.classList.add('o_image');
                return linkEl;
            }));
        },
    },
    ICONS: {
        id: 'ICONS',
        title: "Icons",
        Component: IconSelector,
        save: (selectedMedia) => {
            return selectedMedia.map(icon => {
                const iconEl = document.createElement('i');
                iconEl.classList.add(icon.fontBase, icon.names[0]);
                return iconEl;
            });
        },
    },
    VIDEOS: {
        id: 'VIDEOS',
        title: "Videos",
        Component: VideoSelector,
        save: (selectedMedia) => {
            return selectedMedia.map(video => {
                const template = document.createElement('template');
                template.innerHTML = qweb.render('web_editor.videoWrapper', { src: video.src });
                return template.content.firstChild;
            });
        },
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
            this.addTab(TABS.ICONS);
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
