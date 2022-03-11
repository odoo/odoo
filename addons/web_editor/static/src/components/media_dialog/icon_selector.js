/** @odoo-module */

import fonts from 'wysiwyg.fonts';
import { SearchMedia } from './search_media';

const { Component, useState, useEffect } = owl;

export class IconSelector extends Component {
    setup() {
        fonts.computeFonts();

        this.allFonts = fonts.fontIcons.map(({cssData, base}) => {
            const uniqueIcons = Array.from(new Map(cssData.map(icon => {
                const alias = icon.names.join(',');
                const id = `${base}_${alias}`;
                return [id, { ...icon, alias, id }];
            })).values());
            return { base, icons: uniqueIcons };
        });

        this.state = useState({
            fonts: this.allFonts,
            needle: '',
        });

        this.searchPlaceholder = this.env._t("Search a pictogram");

        useEffect(() => {
            const initWithMedia = async () => {
                if (this.props.media) {
                    const classes = this.props.media.className.split(/\s+/);
                    const mediaFont = this.allFonts.filter(font => classes.includes(font.base))[0];
                    if (mediaFont) {
                        const selectedIcon = mediaFont.icons.filter(icon => {
                            for (const name of icon.names) {
                                if (classes.includes(name)) {
                                    return true;
                                }
                            }
                            return false;
                        })[0];
                        if (selectedIcon) {
                            this.props.setInitialIconClasses(selectedIcon.names);
                            await this.props.selectMedia(selectedIcon, { save: false });
                        }
                    }
                }
            };

            initWithMedia();
        }, () => []);
    }

    get selectedMediaIds() {
        return this.props.selectedMedia[this.props.id].map(({ id }) => id);
    }

    search(needle) {
        this.state.needle = needle;
        if (!this.state.needle) {
            this.state.fonts = this.allFonts;
        } else {
            this.state.fonts = this.allFonts.map(font => {
                const icons = font.icons.filter(icon => icon.alias.indexOf(this.state.needle) >= 0);
                return {...font, icons};
            });
        }
    }

    selectMedia(font, icon) {
        this.props.selectMedia({...icon,
            fontBase: font.base,
        });
    }
}
IconSelector.template = 'web_editor.IconSelector';
IconSelector.components = {
    SearchMedia,
};

export const saveIcons = (selectedMedia) => {
    return selectedMedia.map(icon => {
        const iconEl = document.createElement('span');
        iconEl.classList.add(icon.fontBase, icon.names[0]);
        return iconEl;
    });
};
export const iconSpecificClasses = [];
export const iconTagNames = ['SPAN', 'I'];
