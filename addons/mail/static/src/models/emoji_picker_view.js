/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { attr, clear, many, one, Model } from "@mail/model";

Model({
    name: "EmojiPickerView",
    template: "mail.EmojiPickerView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
        useUpdateToModel({ methodName: "onComponentUpdate", modelName: "EmojiPickerView" });
    },
    lifecycleHooks: {
        _created() {
            if (!this.messaging.device.isSmall) {
                this.update({ isDoFocus: true });
            }
            if (this.messaging.emojiRegistry.isLoaded || this.messaging.emojiRegistry.isLoading) {
                return;
            }
            this.messaging.emojiRegistry.loadEmojiData();
        },
    },
    recordMethods: {
        /**
         * Handles OWL update on the search bar.
         */
        onComponentUpdate() {
            this._handleFocus();
        },
        onFocusinInput() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFocused: true });
        },
        onFocusoutInput() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFocused: false });
        },
        /**
         * @public
         */
        onInput() {
            if (!this.exists()) {
                return;
            }
            this.update({ currentSearch: this.inputRef.el.value });
        },
        /**
         * @public
         */
        reset() {
            this.update({ currentSearch: "" });
            this.inputRef.el.value = "";
        },
        /**
         * @private
         */
        _handleFocus() {
            if (this.isDoFocus) {
                if (!this.inputRef.el) {
                    return;
                }
                this.update({ isDoFocus: false });
                this.inputRef.el.focus();
            }
        },
    },
    fields: {
        __dummyActionView: one("EmojiPickerHeaderActionView", { inverse: "__ownerAsDummy" }),
        actionViews: many("EmojiPickerHeaderActionView", {
            inverse: "owner",
            sort: [["smaller-first", "sequence"]],
        }),
        activeCategoryByGridViewScroll: one("EmojiPickerView.Category"),
        activeCategory: one("EmojiPickerView.Category", {
            compute() {
                if (this.currentSearch !== "") {
                    return clear();
                }
                if (this.activeCategoryByGridViewScroll) {
                    return this.activeCategoryByGridViewScroll;
                }
                if (this.defaultActiveCategory) {
                    return this.defaultActiveCategory;
                }
                return clear();
            },
            inverse: "emojiPickerViewAsActive",
        }),
        categories: many("EmojiPickerView.Category", {
            inverse: "emojiPickerViewOwner",
            compute() {
                return this.messaging.emojiRegistry.allCategories.map((category) => ({ category }));
            },
        }),
        component: attr(),
        currentSearch: attr({ default: "" }),
        defaultActiveCategory: one("EmojiPickerView.Category", {
            compute() {
                if (this.categories.length === 0) {
                    return clear();
                }
                return this.categories[0];
            },
        }),
        emojiCategoryViews: many("EmojiCategoryView", {
            inverse: "emojiPickerViewOwner",
            compute() {
                return this.categories.map((category) => ({ viewCategory: category }));
            },
        }),
        emojiGridView: one("EmojiGridView", {
            default: {},
            inverse: "emojiPickerViewOwner",
            readonly: true,
            required: true,
        }),
        inputRef: attr({ ref: "input" }),
        isDoFocus: attr({ default: false }),
        isFocused: attr({ default: false }),
        placeholder: attr({
            required: true,
            compute() {
                return this.env._t("Search an emoji");
            },
        }),
        popoverViewOwner: one("PopoverView", { identifying: true, inverse: "emojiPickerView" }),
    },
});
