/** @odoo-module **/

import { attr, clear, one, Model } from '@mail/model';

Model({
    name: 'NavigableListItemView',
    template: 'mail.NavigableListItemView',
    recordMethods: {
        onMouseEnter() {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: true });
        },
        onMouseLeave() {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: false });
        },
    },
    fields: {
        composerSuggestionView: one('ComposerSuggestionView', { inverse: 'navigableListItemViewOwner',
            compute() {
                return this.navigableListView && this.navigableListView.ownerAsComposerSuggestion ? {} : clear();
            }
        }),
        /**
         * Determines the record that is content of this dropdown item view.
         */
        content: one('Record', { required: true,
            compute() {
                if (this.composerSuggestionView) {
                    return this.composerSuggestionView;
                }
                return clear();
            },
        }),
        /**
         * Determines the class name for the component
         * that is content of this dropdown item view.
         */
        contentClassName: attr({ default: '',
            compute() {
                if (this.composerSuggestionView) {
                    return 'o_DropdownItemView_composerSuggestion';
                }
                return clear();
            },
        }),
        /**
         * Determines the component name of the content.
         */
        contentComponentName: attr({ default: '', required: true,
            compute() {
                if (this.composerSuggestionView) {
                    return 'ComposerSuggestionView';
                }
                return clear();
            },
        }),
        isActive: attr({
            compute() {
                if (this.navigableListView && this.navigableListView.activeItem === this) {
                    return true;
                }
                return false;
            }
        }),
        isHovered: attr({ default: false }),
        navigableListMainOrExtraItemView: one('NavigableListMainOrExtraItemView', { identifying: true, inverse: 'itemView' }),
        navigableListView: one('NavigableListView', { inverse: 'items',
            compute() {
                return this.navigableListMainOrExtraItemView.navigableListView;
            }
        }),
        suggestable: one('Suggestable', {
            compute() {
                if (this.navigableListMainOrExtraItemView.extraItemViewOwner) {
                    return this.navigableListMainOrExtraItemView.extraItemViewOwner.suggestable;
                } else if (this.navigableListMainOrExtraItemView.mainItemViewOwner) {
                    return this.navigableListMainOrExtraItemView.mainItemViewOwner.suggestable;
                } else {
                    return clear();
                }
            }
        }),
    },
});
