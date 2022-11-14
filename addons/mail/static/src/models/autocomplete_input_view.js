/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { attr, clear, one, Model } from "@mail/model";

import { onMounted, onWillUnmount } from "@odoo/owl";

Model({
    name: "AutocompleteInputView",
    template: "mail.AutocompleteInputView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
        onMounted(() => {
            if (!this.root.el) {
                return;
            }
            if (this.isFocusOnMount) {
                this.root.el.focus();
            }
            const args = {
                autoFocus: true,
                select: (ev, ui) => {
                    this.onSelect(ev, ui);
                },
                source: (req, res) => {
                    this.onSource(req, res);
                },
                html: this.isHtml,
            };
            if (this.customClass) {
                args.classes = { "ui-autocomplete": this.customClass };
            }
            const autoCompleteElem = $(this.root.el).autocomplete(args);
            // Resize the autocomplete dropdown options to handle the long strings
            // By setting the width of dropdown based on the width of the input element.
            autoCompleteElem.data("ui-autocomplete")._resizeMenu = function () {
                const ul = this.menu.element;
                ul.outerWidth(this.element.outerWidth());
            };
        });
        onWillUnmount(() => {
            if (!this.root.el) {
                return;
            }
            $(this.root.el).autocomplete("destroy");
        });
    },
    identifyingMode: "xor",
    recordMethods: {
        onBlur() {
            if (!this.exists()) {
                return;
            }
            if (this.discussSidebarCategoryOwnerAsAddingItem) {
                this.discussSidebarCategoryOwnerAsAddingItem.onHideAddingItem();
                return;
            }
            if (this.discussViewOwnerAsMobileAddItemHeader) {
                this.discussViewOwnerAsMobileAddItemHeader.onHideMobileAddItemHeader();
                return;
            }
            if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                this.messagingMenuOwnerAsMobileNewMessageInput.onHideMobileNewMessage();
                return;
            }
        },
        /**
         * @param {FocusEvent} ev
         */
        onFocusin(ev) {
            if (!this.exists()) {
                return;
            }
            if (this.chatWindowOwnerAsNewMessage) {
                this.chatWindowOwnerAsNewMessage.onFocusInNewMessageFormInput(ev);
                return;
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onKeydown(ev) {
            if (!this.exists()) {
                return;
            }
            if (ev.key === "Escape") {
                this.onBlur();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onSelect(ev, ui) {
            if (!this.exists()) {
                return;
            }
            if (this.chatWindowOwnerAsNewMessage) {
                this.chatWindowOwnerAsNewMessage.onAutocompleteSelect(ev, ui);
                return;
            }
            if (this.discussSidebarCategoryOwnerAsAddingItem) {
                this.discussSidebarCategoryOwnerAsAddingItem.onAddItemAutocompleteSelect(ev, ui);
                return;
            }
            if (this.discussViewOwnerAsMobileAddItemHeader) {
                this.discussViewOwnerAsMobileAddItemHeader.onMobileAddItemHeaderInputSelect(ev, ui);
                return;
            }
            if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                this.messagingMenuOwnerAsMobileNewMessageInput.onMobileNewMessageInputSelect(
                    ev,
                    ui
                );
                return;
            }
        },
        /**
         * @param {Object} req
         * @param {function} res
         */
        onSource(req, res) {
            if (!this.exists()) {
                return;
            }
            if (this.chatWindowOwnerAsNewMessage) {
                this.chatWindowOwnerAsNewMessage.onAutocompleteSource(req, res);
                return;
            }
            if (this.discussSidebarCategoryOwnerAsAddingItem) {
                this.discussSidebarCategoryOwnerAsAddingItem.onAddItemAutocompleteSource(req, res);
                return;
            }
            if (this.discussViewOwnerAsMobileAddItemHeader) {
                this.discussViewOwnerAsMobileAddItemHeader.onMobileAddItemHeaderInputSource(
                    req,
                    res
                );
                return;
            }
            if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                this.messagingMenuOwnerAsMobileNewMessageInput.onMobileNewMessageInputSource(
                    req,
                    res
                );
                return;
            }
        },
    },
    fields: {
        chatWindowOwnerAsNewMessage: one("ChatWindow", {
            identifying: true,
            inverse: "newMessageAutocompleteInputView",
        }),
        component: attr(),
        customClass: attr({
            default: "",
            compute() {
                if (this.discussSidebarCategoryOwnerAsAddingItem) {
                    if (
                        this.discussSidebarCategoryOwnerAsAddingItem ===
                        this.messaging.discuss.categoryChannel
                    ) {
                        return "o_DiscussSidebarCategory_newChannelAutocompleteSuggestions";
                    }
                }
                if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                    return (
                        this.messagingMenuOwnerAsMobileNewMessageInput.viewId +
                        "_mobileNewMessageInputAutocomplete"
                    );
                }
                return clear();
            },
        }),
        discussSidebarCategoryOwnerAsAddingItem: one("DiscussSidebarCategory", {
            identifying: true,
            inverse: "addingItemAutocompleteInputView",
        }),
        discussViewOwnerAsMobileAddItemHeader: one("DiscussView", {
            identifying: true,
            inverse: "mobileAddItemHeaderAutocompleteInputView",
        }),
        isFocusOnMount: attr({
            default: false,
            compute() {
                if (this.discussViewOwnerAsMobileAddItemHeader) {
                    return true;
                }
                if (this.discussSidebarCategoryOwnerAsAddingItem) {
                    return true;
                }
                if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                    return true;
                }
                return clear();
            },
        }),
        isHtml: attr({
            default: false,
            compute() {
                if (this.discussViewOwnerAsMobileAddItemHeader) {
                    return this.discussViewOwnerAsMobileAddItemHeader.isAddingChannel;
                }
                if (this.discussSidebarCategoryOwnerAsAddingItem) {
                    return (
                        this.discussSidebarCategoryOwnerAsAddingItem ===
                        this.messaging.discuss.categoryChannel
                    );
                }
                return clear();
            },
        }),
        messagingMenuOwnerAsMobileNewMessageInput: one("MessagingMenu", {
            identifying: true,
            inverse: "mobileNewMessageAutocompleteInputView",
        }),
        placeholder: attr({
            compute() {
                if (this.chatWindowOwnerAsNewMessage) {
                    return this.chatWindowOwnerAsNewMessage.newMessageFormInputPlaceholder;
                }
                if (this.discussViewOwnerAsMobileAddItemHeader) {
                    if (this.discussViewOwnerAsMobileAddItemHeader.isAddingChannel) {
                        return this.discussViewOwnerAsMobileAddItemHeader.discuss
                            .addChannelInputPlaceholder;
                    } else {
                        return this.discussViewOwnerAsMobileAddItemHeader.discuss
                            .addChatInputPlaceholder;
                    }
                }
                if (this.discussSidebarCategoryOwnerAsAddingItem) {
                    return this.discussSidebarCategoryOwnerAsAddingItem.newItemPlaceholderText;
                }
                if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                    return this.messagingMenuOwnerAsMobileNewMessageInput
                        .mobileNewMessageInputPlaceholder;
                }
                return clear();
            },
        }),
    },
});
