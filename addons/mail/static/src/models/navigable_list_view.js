/** @odoo-module **/

import { attr, clear, many, one, Model } from '@mail/model';

Model({
    name: 'NavigableListView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * Returns whether the given html element is inside the component
         * of this popover view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        contains(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        // onResize() {
        //     if (!this.exists()) {
        //         return;
        //     }
        //     if (!this.component.root.el || !this.anchorRef || !this.anchorRef.el) {
        //         return;
        //     }
        //     const { width } = this.anchorRef.el.getBoundingClientRect();
        //     this.update({ width });
        // },
        /**
         * Sets the first dropdownItem as active. Main and extra records are
         * considered together.
         */
        setFirstActive() {
            const firstItem = this.items[0];
            this.update({ userExplicitSelection: firstItem });
        },
        /**
         * Sets the last dropdownItem as active. Main and extra records are
         * considered together.
         */
        setLastActive() {
            const { length, [length - 1]: lastItem } = this.items;
            this.update({ userExplicitSelection: lastItem });
        },
        /**
         * Sets the next dropdownItem as active. Main and extra records are
         * considered together.
         */
        setNextActive() {
            const activeIndex = this.items.findIndex(
                item => item === this.activeItem
            );
            if (activeIndex === this.items.length - 1) {
                // loop when reaching the end of the list
                this.setFirstActive();
                return;
            }
            const nextDropdownItemView = this.items[activeIndex + 1];
            this.update({ userExplicitSelection: nextDropdownItemView });
        },
        /**
         * Sets the previous dropdownItem as active. Main and extra records are
         * considered together.
         */
        setPreviousActive() {
            const activeIndex = this.items.findIndex(
                item => item === this.activeItem
            );
            if (activeIndex === 0) {
                // loop when reaching the start of the list
                this.setLastActive();
                return;
            }
            const previousDropdownItemView = this.items[activeIndex - 1];
            this.update({ userExplicitSelection: previousDropdownItemView });
        },
    },
    fields: {
        activeItem: one('NavigableListItemView', {
            compute() {
                if (this.items.includes(this.userExplicitSelection)) {
                    return this.userExplicitSelection;
                }
                const firstNavigableListItemView = this.items[0];
                return firstNavigableListItemView;
            },
        }),
        anchorRef: attr({ required: true,
            compute() {
                if (this.ownerAsComposerSuggestion) {
                    return this.ownerAsComposerSuggestion.textInput.textareaRef;
                }
                return clear();
            },
        }),
        component: attr(),
        extraItems: many('NavigableListExtraItemView', { inverse: 'navigableListViewOwner',
            compute() {
                if (this.ownerAsComposerSuggestion) {
                    return this.ownerAsComposerSuggestion.extraSuggestions.map(suggestable => ({ suggestable }));
                }
                return clear();
            },
        }),
        hasToScrollToActiveItem: attr({ default: false }),
        items: many('NavigableListItemView', { inverse: 'navigableListView' }),
        mainItems: many('NavigableListMainItemView', { inverse: 'navigableListViewOwner',
            compute() {
                if (this.ownerAsComposerSuggestion) {
                    return this.ownerAsComposerSuggestion.mainSuggestions.map(suggestable => ({ suggestable }));
                }
                return clear();
            },
        }),
        navigableListPopoverView: one('PopoverView', { inverse: 'navigableListViewOwner',
            compute() {
                return this.items.length > 0 ? {} : clear();
            },
        }),
        ownerAsComposerSuggestion: one('ComposerView', { identifying: true, inverse: 'navigableListViewAsSuggestion' }),
        /**
         * Position of the dropdown menu view relative to its anchor point.
         * Valid values: 'Direction | Variant'
         * Direction: 'top' | 'left' | 'bottom' | 'right'
         * Variant: 'start' | 'middle' | 'end'
         */
        position: attr({
            compute() {
                if (this.ownerAsComposerSuggestion) {
                    return 'top-start';
                }
                return 'bottom';
            },
        }),
        userExplicitSelection: one('NavigableListItemView'),
        width: attr(),
    },
});
