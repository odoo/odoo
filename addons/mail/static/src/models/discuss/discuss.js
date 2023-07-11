/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, unlink } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Discuss extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickStartAMeetingButton = this.onClickStartAMeetingButton.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        clearIsAddingItem() {
            this.update({
                addingChannelValue: "",
                isAddingChannel: false,
                isAddingChat: false,
            });
        }

        /**
         * Close the discuss app. Should reset its internal state.
         */
        close() {
            this.update({ isOpen: false });
        }

        focus() {
            if (this.threadView && this.threadView.composerView) {
                this.threadView.composerView.update({ doFocus: true });
            }
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async handleAddChannelAutocompleteSelect(ev, ui) {
            // Necessary in order to prevent AutocompleteSelect event's default
            // behaviour as html tags visible for a split second in text area
            ev.preventDefault();
            const name = this.addingChannelValue;
            this.clearIsAddingItem();
            if (ui.item.special) {
                const channel = await this.async(() =>
                    this.messaging.models['mail.thread'].performRpcCreateChannel({
                        name,
                        privacy: ui.item.special === 'private' ? 'private' : 'groups',
                    })
                );
                channel.open();
            } else {
                const channel = this.messaging.models['mail.thread'].insert({
                    id: ui.item.id,
                    model: 'mail.channel',
                });
                await channel.join();
                // Channel must be pinned immediately to be able to open it before
                // the result of join is received on the bus.
                channel.update({ isServerPinned: true });
                channel.open();
            }
        }

        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        async handleAddChannelAutocompleteSource(req, res) {
            this.update({ addingChannelValue: req.term });
            const threads = await this.messaging.models['mail.thread'].searchChannelsToOpen({ limit: 10, searchTerm: req.term });
            const items = threads.map((thread) => {
                const escapedName = owl.utils.escape(thread.name);
                return {
                    id: thread.id,
                    label: escapedName,
                    value: escapedName,
                };
            });
            const escapedValue = owl.utils.escape(req.term);
            // XDU FIXME could use a component but be careful with owl's
            // renderToString https://github.com/odoo/owl/issues/708
            items.push({
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-hashtag"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'public'
            }, {
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-lock"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'private'
            });
            res(items);
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        handleAddChatAutocompleteSelect(ev, ui) {
            this.messaging.openChat({ partnerId: ui.item.id });
            this.clearIsAddingItem();
        }

        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        handleAddChatAutocompleteSource(req, res) {
            const value = owl.utils.escape(req.term);
            this.messaging.models['mail.partner'].imSearch({
                callback: partners => {
                    const suggestions = partners.map(partner => {
                        return {
                            id: partner.id,
                            value: partner.nameOrDisplayName,
                            label: partner.nameOrDisplayName,
                        };
                    });
                    res(_.sortBy(suggestions, 'label'));
                },
                keyword: value,
                limit: 10,
            });
        }

        /**
         * Handles click on the mobile "new chat" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChatButton(ev) {
            this.update({ isAddingChat: true });
        }

        /**
         * Handles click on the mobile "new channel" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChannelButton(ev) {
            this.update({ isAddingChannel: true });
        }

        /**
         * Handles click on the "Start a meeting" button.
         *
         * @param {MouseEvent} ev
         */
        async onClickStartAMeetingButton(ev) {
            const meetingChannel = await this.messaging.models['mail.thread'].createGroupChat({
                default_display_mode: 'video_full_screen',
                partners_to: [this.messaging.currentPartner.id],
            });
            meetingChannel.toggleCall({ startWithVideo: true });
            await meetingChannel.open({ focus: false });
            if (!meetingChannel.exists() || !this.threadView) {
                return;
            }
            this.threadView.topbar.openInvitePopoverView();
        }

        /**
         * Opens thread from init active id if the thread exists.
         */
        openInitThread() {
            const [model, id] = typeof this.initActiveId === 'number'
                ? ['mail.channel', this.initActiveId]
                : this.initActiveId.split('_');
            const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: model !== 'mail.box' ? Number(id) : id,
                model,
            });
            if (!thread) {
                return;
            }
            thread.open();
            if (this.messaging.device.isMobile && thread.channel_type) {
                this.update({ activeMobileNavbarTabId: thread.channel_type });
            }
        }


        /**
         * Opens the given thread in Discuss, and opens Discuss if necessary.
         *
         * @param {mail.thread} thread
         * @param {Object} [param1={}]
         * @param {Boolean} [param1.focus]
         */
        async openThread(thread, { focus } = {}) {
            this.update({
                thread: link(thread),
            });
            if (focus !== undefined ? focus : !this.messaging.device.isMobileDevice) {
                this.focus();
            }
            if (!this.isOpen) {
                this.env.bus.trigger('do-action', {
                    action: 'mail.action_discuss',
                    options: {
                        name: this.env._t("Discuss"),
                        active_id: this.threadToActiveId(this),
                        clear_breadcrumbs: false,
                        on_reverse_breadcrumb: () => this.close(), // this is useless, close is called by destroy anyway
                    },
                });
            }
        }

        /**
         * @param {mail.thread} thread
         * @returns {string}
         */
        threadToActiveId(thread) {
            return `${thread.model}_${thread.id}`;
        }

        /**
         * @param {string} value
         */
        onInputQuickSearch(value) {
            // Opens all categories only when user starts to search from empty search value.
            if (!this.sidebarQuickSearchValue) {
                this.categoryChat.open();
                this.categoryChannel.open();
            }
            this.update({ sidebarQuickSearchValue: value });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeActiveId() {
            if (!this.thread) {
                return clear();
            }
            return this.threadToActiveId(this.thread);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeAddingChannelValue() {
            if (!this.isOpen) {
                return "";
            }
            return this.addingChannelValue;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            if (!this.thread || !this.isOpen) {
                return false;
            }
            if (
                this.messaging.device.isMobile &&
                (
                    this.activeMobileNavbarTabId !== 'mailbox' ||
                    this.thread.model !== 'mail.box'
                )
            ) {
                return false;
            }
            return true;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChannel() {
            if (!this.isOpen) {
                return false;
            }
            return this.isAddingChannel;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChat() {
            if (!this.isOpen) {
                return false;
            }
            return this.isAddingChat;
        }

        /**
         * Only pinned threads are allowed in discuss.
         *
         * @private
         * @returns {mail.thread|undefined}
         */
        _computeThread() {
            if (!this.thread || !this.thread.isPinned) {
                return unlink();
            }
        }

        /**
         * @private
         * @returns {mail.thread_viewer}
         */
        _computeThreadViewer() {
            return insertAndReplace({
                hasMemberList: true,
                hasThreadView: this.hasThreadView,
                hasTopbar: true,
                thread: this.thread ? link(this.thread) : unlink(),
            });
        }
    }

    Discuss.fields = {
        activeId: attr({
            compute: '_computeActiveId',
        }),
        /**
         * Active mobile navbar tab, either 'mailbox', 'chat', or 'channel'.
         */
        activeMobileNavbarTabId: attr({
            default: 'mailbox',
        }),
        /**
         * Value that is used to create a channel from the sidebar.
         */
        addingChannelValue: attr({
            compute: '_computeAddingChannelValue',
            default: "",
        }),
        /**
         * Discuss sidebar category for `channel` type channel threads.
         */
        categoryChannel: one2one('mail.discuss_sidebar_category', {
            inverse: 'discussAsChannel',
            isCausal: true,
        }),
        /**
         * Discuss sidebar category for `chat` type channel threads.
         */
        categoryChat: one2one('mail.discuss_sidebar_category', {
            inverse: 'discussAsChat',
            isCausal: true,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute: '_computeHasThreadView',
        }),
        /**
         * Formatted init thread on opening discuss for the first time,
         * when no active thread is defined. Useful to set a thread to
         * open without knowing its local id in advance.
         * Support two formats:
         *    {string} <threadModel>_<threadId>
         *    {int} <channelId> with default model of 'mail.channel'
         */
        initActiveId: attr({
            default: 'mail.box_inbox',
        }),
        /**
         * Determine whether current user is currently adding a channel from
         * the sidebar.
         */
        isAddingChannel: attr({
            compute: '_computeIsAddingChannel',
            default: false,
        }),
        /**
         * Determine whether current user is currently adding a chat from
         * the sidebar.
         */
        isAddingChat: attr({
            compute: '_computeIsAddingChat',
            default: false,
        }),
        /**
         * Determines if the logic for opening a thread via the `initActiveId`
         * has been processed. This is necessary to ensure that this only
         * happens once.
         */
        isInitThreadHandled: attr({
            default: false,
        }),
        /**
         * Whether the discuss app is open or not. Useful to determine
         * whether the discuss or chat window logic should be applied.
         */
        isOpen: attr({
            default: false,
        }),
        /**
         * The menu_id of discuss app, received on mail/init_messaging and
         * used to open discuss from elsewhere.
         */
        menu_id: attr({
            default: null,
        }),
        /**
         * Quick search input value in the discuss sidebar (desktop). Useful
         * to filter channels and chats based on this input content.
         */
        sidebarQuickSearchValue: attr({
            default: "",
        }),
        /**
         * States the OWL ref of the start a meeting button in sidebar.
         * Useful to provide anchor for the invite popover positioning.
         */
        startAMeetingButtonRef: attr(),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        thread: many2one('mail.thread', {
            compute: '_computeThread',
        }),
        /**
         * States the `mail.thread_view` displaying `this.thread`.
         */
        threadView: one2one('mail.thread_view', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `mail.thread_viewer` managing the display of `this.thread`.
         */
        threadViewer: one2one('mail.thread_viewer', {
            compute: '_computeThreadViewer',
            inverse: 'discuss',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    };
    Discuss.identifyingFields = ['messaging'];
    Discuss.modelName = 'mail.discuss';

    return Discuss;
}

registerNewModel('mail.discuss', factory);
