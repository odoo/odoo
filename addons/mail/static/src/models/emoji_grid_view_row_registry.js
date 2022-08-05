/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridViewRowRegistry',
    identifyingMode: 'xor',
    recordMethods: {
        computeNonSearchRows() {
            const value = [];
            let index = 0;
            for (let category of this.messaging.emojiRegistry.allCategories) {
                value.push({ category, index });
                index++;
                let currentItems = [];
                for (let emojiInCategory of category.allEmojiInCategoryOfCurrent) {
                    currentItems.push({ emojiOrEmojiInCategory: { emojiInCategory } });
                    if (currentItems.length === this.emojiGridViewOwner.amountOfItemsPerRow) {
                        index++;
                        value.push({ items: currentItems, index });
                        currentItems = [];
                    }
                }
            }
            return value;
        },
        _sortRows() {
            return [
                ['smaller-first', 'index'],
            ];
        },
    },
    fields: {
        rows: many('EmojiGridRowView', {
            compute() {
                if (!this.emojiGridViewOwner) {
                    return clear();
                }
                if (this.emojiGridViewOwnerAsNonSearch) {
                    return this.computeNonSearchRows();
                }
                if (this.emojiGridViewOwnerAsSearch) {
                    if (this.emojiGridViewOwner.emojiPickerViewOwner.emojiSearchBarView.currentSearch === "") {
                        return this.computeNonSearchRows();
                    }
                    const emojis = this.messaging.emojiRegistry.allEmojis.filter(this.emojiGridViewOwner._filterEmoji);
                    const value = [];
                    let index = 0;
                    let currentItems = [];
                    for (let emoji of emojis) {
                        currentItems.push({ emojiOrEmojiInCategory: { emoji } });
                        if (currentItems.length === this.emojiGridViewOwner.amountOfItemsPerRow) {
                            index++;
                            value.push({ items: currentItems, index });
                            currentItems = [];
                        }
                    }
                    return value;
                }
                return clear();
            },
            isCausal: true,
            inverse: 'emojiGridViewRowRegistryOwner',
            sort: '_sortRows',
        }),
        emojiGridViewOwner: one('EmojiGridView', {
            compute() {
                return this.emojiGridViewOwnerAsNonSearch || this.emojiGridViewOwnerAsSearch;
            },
        }),
        emojiGridViewOwnerAsNonSearch: one('EmojiGridView', {
            identifying: true,
            inverse: 'nonSearchRowRegistry',
        }),
        emojiGridViewOwnerAsSearch: one('EmojiGridView', {
            identifying: true,
            inverse: 'searchRowRegistry',
        }),
    },
});
