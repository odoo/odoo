odoo.define('web_editor.wysiwyg', function (require) {
'use strict';

const { ComponentWrapper } = require('web.OwlCompatibility');
const { MediaDialogWrapper } = require('@web_editor/components/media_dialog/media_dialog');
const { VideoSelector } = require('@web_editor/components/media_dialog/video_selector');
const dom = require('web.dom');
const core = require('web.core');
const { browser } = require('@web/core/browser/browser');
const Widget = require('web.Widget');
const Dialog = require('web.Dialog');
const customColors = require('web_editor.custom_colors');
const {ColorPaletteWidget} = require('web_editor.ColorPalette');
const {ColorpickerWidget} = require('web.Colorpicker');
const concurrency = require('web.concurrency');
const { device } = require('web.config');
const { localization } = require('@web/core/l10n/localization');
const OdooEditorLib = require('@web_editor/js/editor/odoo-editor/src/OdooEditor');
const snippetsEditor = require('web_editor.snippet.editor');
const Toolbar = require('web_editor.toolbar');
const weWidgets = require('wysiwyg.widgets');
const Link = require('wysiwyg.widgets.Link');
const wysiwygUtils = require('@web_editor/js/common/wysiwyg_utils');
const weUtils = require('web_editor.utils');
const { PeerToPeer, RequestError } = require('@web_editor/js/wysiwyg/PeerToPeer');
const { Mutex } = require('web.concurrency');
const snippetsOptions = require('web_editor.snippets.options');
const { peek } = require('@web_editor/js/editor/odoo-editor/src/utils/utils');
var _t = core._t;
const QWeb = core.qweb;

const OdooEditor = OdooEditorLib.OdooEditor;
const getDeepRange = OdooEditorLib.getDeepRange;
const getInSelection = OdooEditorLib.getInSelection;
const isBlock = OdooEditorLib.isBlock;
const rgbToHex = OdooEditorLib.rgbToHex;
const preserveCursor = OdooEditorLib.preserveCursor;
const closestElement = OdooEditorLib.closestElement;
const setSelection = OdooEditorLib.setSelection;
const endPos = OdooEditorLib.endPos;
const hasValidSelection = OdooEditorLib.hasValidSelection;
const parseHTML = OdooEditorLib.parseHTML;

var id = 0;
const basicMediaSelector = 'img, .fa, .o_image, .media_iframe_video';
// (see isImageSupportedForStyle).
const mediaSelector = basicMediaSelector.split(',').map(s => `${s}:not([data-oe-xpath])`).join(',');

// Time to consider a user offline in ms. This fixes the problem of the
// navigator closing rtc connection when the mac laptop screen is closed.
const CONSIDER_OFFLINE_TIME = 1000;
// Check wether the computer could be offline. This fixes the problem of the
// navigator closing rtc connection when the mac laptop screen is closed.
// This case happens on Mac OS on every browser when the user close it's laptop
// screen. At first, the os/navigator closes all rtc connection, and after some
// times, the os/navigator internet goes offline without triggering an
// offline/online event.
// However, if the laptop screen is open and the connection is properly remove
// (e.g. disconnect wifi), the event is properly triggered.
const CHECK_OFFLINE_TIME = 1000;
const PTP_CLIENT_DISCONNECTED_STATES = [
    'failed',
    'closed',
    'disconnected',
];

// Time in ms to wait when trying to aggregate snapshots from other peers and
// potentially recover from a missing step before trying to apply those
// snapshots or recover from the server.
const PTP_MAX_RECOVERY_TIME = 500;

const REQUEST_ERROR = Symbol('REQUEST_ERROR');

// this is a local cache for ice server descriptions
let ICE_SERVERS = null;

const Wysiwyg = Widget.extend({
    defaultOptions: {
        lang: 'odoo',
        colors: customColors,
        recordInfo: {context: {}},
        document: document,
        allowCommandVideo: true,
        allowCommandImage: true,
        allowCommandLink: true,
        insertParagraphAfterColumns: true,
        autostart: true,
    },
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.id = ++id;
        this.options = this._getEditorOptions(options);
        this.saving_mutex = new concurrency.Mutex();
        // Keeps track of color palettes per event name.
        this.colorpickers = {};
        this._onDocumentMousedown = this._onDocumentMousedown.bind(this);
        this._onBlur = this._onBlur.bind(this);
        this._onScroll = this._onScroll.bind(this);
        this.customizableLinksSelector = 'a'
            + ':not([data-bs-toggle="tab"])'
            + ':not([data-bs-toggle="collapse"])'
            + ':not([data-bs-toggle="dropdown"])'
            + ':not(.dropdown-item)';
        // navigator.onLine is sometimes a false positive, this._isOnline use
        // more heuristics to bypass the limitation.
        this._isOnline = true;
        this._signalOnline = this._signalOnline.bind(this);
        this.tooltipTimeouts = [];
        Wysiwyg.activeWysiwygs.add(this);
        this._oNotEditableObservers = new Map();
        this._joinPeerToPeer = this._joinPeerToPeer.bind(this);
    },
    /**
     *
     * @override
     */
    start: async function () {
        await this._super.apply(this, arguments);
        // If this widget is started from the OWL legacy component, at the time
        // of start, the $el is not in the document yet. Some instruction in the
        // start rely on the $el being in the document at that time, including
        // code for the collaboration (for adding cursors) or the iframe loading
        // in mass_mailing.
        if (this.options.autostart) {
            return this.startEdition();
        }
    },
    startEdition: async function () {
        const self = this;

        const options = this.options;

        this.$editable = this.$editable || this.$el;
        if (options.value) {
            this.$editable.html(options.value);
        }

        this._isDocumentStale = false;

        // Each time a reset of the document is triggered, it is assigned a
        // unique identifier. Since resetting the editor involves asynchronous
        // requests, it is possible that subsequent resets are triggered before
        // the previous one is complete. This property identifies the latest
        // reset and can be compared against to cancel the processing of late
        // responses from previous resets.
        this._lastCollaborationResetId = 0;
        // This ID correspond to the peer that initiated the document and set
        // the initial oid for all nodes in the tree. It is not the same as
        // document that had a step id at some point. If a step comes from a
        // different history, we should not apply it.
        this._historyShareId = Math.floor(Math.random() * Math.pow(2,52)).toString();

        // The ID is the latest step ID that the server knows through
        // `data-last-history-steps`. We cannot save to the server if we do not
        // have that ID in our history ids as it means that our version is
        // stale.
        this._serverLastStepId = options.value && this._getLastHistoryStepId(options.value);

        this.$editable.data('wysiwyg', this);
        this.$editable.data('oe-model', options.recordInfo.res_model);
        this.$editable.data('oe-id', options.recordInfo.res_id);
        document.addEventListener('mousedown', this._onDocumentMousedown, true);
        this._bindOnBlur();

        this.toolbar = new Toolbar(this, this.options.toolbarTemplate);
        await this.toolbar.appendTo(document.createElement('void'));
        const powerboxOptions = this._getPowerboxOptions();

        let editorCollaborationOptions;
        if (
            options.collaborationChannel &&
            // Hack: check if mail module is installed.
            this.getSession()['notification_type']
        ) {
            this._currentClientId = this._generateClientId();
            editorCollaborationOptions = this.setupCollaboration(options.collaborationChannel);
            // Wait until editor is focused to join the peer to peer network.
            this.$editable[0].addEventListener('focus', this._joinPeerToPeer);
        }

        const getYoutubeVideoElement = async (url) => {
            const { embed_url: src } = await this._rpc({
                route: '/web_editor/video_url/data',
                params: { video_url: url },
            });
            const [savedVideo] = VideoSelector.createElements([{src}]);
            savedVideo.classList.add(...VideoSelector.mediaSpecificClasses);
            return savedVideo;
        };

        this.odooEditor = new OdooEditor(this.$editable[0], Object.assign({
            _t: _t,
            toolbar: this.toolbar.$el[0],
            document: this.options.document,
            autohideToolbar: !!this.options.autohideToolbar,
            isRootEditable: this.options.isRootEditable,
            onPostSanitize: this._setONotEditable.bind(this),
            placeholder: this.options.placeholder,
            powerboxFilters: this.options.powerboxFilters || [],
            showEmptyElementHint: this.options.showEmptyElementHint,
            controlHistoryFromDocument: this.options.controlHistoryFromDocument,
            initialHistoryId: this._serverLastStepId,
            getContentEditableAreas: this.options.getContentEditableAreas,
            getReadOnlyAreas: this.options.getReadOnlyAreas,
            getUnremovableElements: this.options.getUnremovableElements,
            defaultLinkAttributes: this.options.userGeneratedContent ? {rel: 'ugc' } : {},
            allowCommandVideo: this.options.allowCommandVideo,
            allowInlineAtRoot: this.options.allowInlineAtRoot,
            getYoutubeVideoElement: getYoutubeVideoElement,
            getContextFromParentRect: options.getContextFromParentRect,
            getScrollContainerRect: () => {
                if (!this.scrollContainer || !this.scrollContainer.getBoundingClientRect) {
                    this.scrollContainer = document.querySelector('.o_action_manager') || document.body;
                }
                return this.scrollContainer.getBoundingClientRect();
            },
            getPowerboxElement: () => {
                const selection = (this.options.document || document).getSelection();
                if (selection.isCollapsed && selection.rangeCount) {
                    const baseNode = closestElement(selection.anchorNode, 'P, DIV');
                    const fieldContainer = closestElement(selection.anchorNode, '[data-oe-field]');
                    if (!baseNode ||
                        (
                            fieldContainer &&
                            !(
                                fieldContainer.getAttribute('data-oe-field') === 'arch' ||
                                fieldContainer.getAttribute('data-oe-type') === 'html'
                            )
                        )) {
                        return false;
                    }
                    return baseNode;
                }
            },
            isHintBlacklisted: node => {
                return (node.classList && node.classList.contains('nav-item')) || (
                    node.hasAttribute && (
                        node.hasAttribute('data-target') ||
                        node.hasAttribute('data-oe-model')
                    )
                );
            },
            filterMutationRecords: (records) => {
                return records.filter((record) => {
                    return !(
                        (record.target.classList && record.target.classList.contains('o_header_standard')) ||
                        (record.type === 'attributes' && record.attributeName === 'data-last-history-steps')
                    );
                });
            },
            preHistoryUndo: () => {
                if (this.linkTools) {
                    this.linkTools.destroy();
                    this.linkTools = undefined;
                }
            },
            commands: powerboxOptions.commands,
            categories: powerboxOptions.categories,
            plugins: options.editorPlugins,
            direction: options.direction || localization.direction || 'ltr',
            collaborationClientAvatarUrl: this._getCollaborationClientAvatarUrl(),
            renderingClasses: ['o_dirty', 'o_transform_removal', 'oe_edited_link', 'o_menu_loading'],
            foldSnippets: !!options.foldSnippets,
        }, editorCollaborationOptions));

        this.odooEditor.addEventListener('contentChanged', function () {
            self.$editable.trigger('content_changed');
            // todo: to remove when removing the legacy field_html
            self.trigger_up('wysiwyg_change');
        });
        document.addEventListener("mousemove", this._signalOnline, true);
        document.addEventListener("keydown", this._signalOnline, true);
        document.addEventListener("keyup", this._signalOnline, true);
        if (this.odooEditor.document !== document) {
            this.odooEditor.document.addEventListener("mousemove", this._signalOnline, true);
            this.odooEditor.document.addEventListener("keydown", this._signalOnline, true);
            this.odooEditor.document.addEventListener("keyup", this._signalOnline, true);
        }

        this._initialValue = this.getValue();
        const $wrapwrap = $('#wrapwrap');
        if ($wrapwrap.length) {
            $wrapwrap[0].addEventListener('scroll', this.odooEditor.multiselectionRefresh, { passive: true });
            this.$root = this.$root || $wrapwrap;
        }

        this.$editable.on('click', '[data-oe-field][data-oe-sanitize-prevent-edition]', () => {
            Dialog.alert(this, _t("Someone with escalated rights previously modified this area, you are therefore not able to modify it yourself."));
        });

        this._observeOdooFieldChanges();
        this.$editable.on(
            'mousedown touchstart',
            '[data-oe-field]',
            function () {
                self.odooEditor.observerUnactive();
                const $field = $(this);
                if (($field.data('oe-type') === "datetime" || $field.data('oe-type') === "date")) {
                    let selector = '[data-oe-id="' + $field.data('oe-id') + '"]';
                    selector += '[data-oe-field="' + $field.data('oe-field') + '"]';
                    selector += '[data-oe-model="' + $field.data('oe-model') + '"]';
                    const $linkedFieldNodes = self.$editable.find(selector).addBack(selector);
                    $linkedFieldNodes.addClass('o_editable_date_field_linked');
                    if (!$field.hasClass('o_editable_date_field_format_changed')) {
                        $linkedFieldNodes.text($field.data('oe-original-with-format'));
                        $linkedFieldNodes.addClass('o_editable_date_field_format_changed');
                        $linkedFieldNodes.filter('.oe_hide_on_date_edit').addClass('d-none');
                        setTimeout(() => {
                            // we might hide the clicked date, focus the one
                            // supposed to be editable
                            Wysiwyg.setRange($linkedFieldNodes.filter(':not(.oe_hide_on_date_edit)')[0]);
                        }, 0);
                    }
                }
                if ($field.attr('contenteditable') !== 'false') {
                    if ($field.data('oe-type') === "monetary") {
                        $field.attr('contenteditable', false);
                        const $currencyValue = $field.find('.oe_currency_value');
                        $currencyValue.attr('contenteditable', true);
                        $currencyValue.one('mouseup touchend', (e) => {
                            $currencyValue.selectContent();
                        });
                    }
                    if ($field.data('oe-type') === "image") {
                        $field.attr('contenteditable', false);
                        $field.find('img').attr('contenteditable', $field.data('oe-readonly') !== 1);
                    }
                    if ($field.is('[data-oe-many2one-id]')) {
                        $field.attr('contenteditable', false);
                    }
                }
                self.odooEditor.observerActive();
            }
        );

        this.$editable.on('click', '.o_image, .media_iframe_video', e => e.preventDefault());
        this.showTooltip = true;
        this.$editable.on('dblclick', mediaSelector, function () {
            let isEditable =
                // TODO that first check is probably useless/wrong: checking if
                // the media itself has editable content should not be relevant.
                // In fact the content of all media should be marked as non
                // editable anyway.
                this.isContentEditable ||
                // For a media to be editable, the base case is to be in a
                // container whose content is editable.
                (this.parentElement && this.parentElement.isContentEditable);

            if (!isEditable && this.classList.contains('o_editable_media')) {
                isEditable = weUtils.shouldEditableMediaBeEditable(this);
            }

            if (isEditable) {
                self.showTooltip = false;

                const selection = self.odooEditor.document.getSelection();
                const anchorNode = selection.anchorNode;
                if (anchorNode && closestElement(anchorNode, '[data-oe-protected="true"]')) {
                    return;
                }

                const $el = $(this);
                let params = {node: this};
                $el.selectElement();

                if (!$el.parent().hasClass('o_stars')) {
                    // Waiting for all the options to be initialized before
                    // opening the media dialog and only if the media has not
                    // been deleted in the meantime.
                    self.waitForEmptyMutexAction().then(() => {
                        if ($el[0].parentElement) {
                            self.openMediaDialog(params);
                        }
                    });
                }
            }
        });

        if (options.snippets) {
            $(this.odooEditor.document.body).addClass('editor_enable');
            this.snippetsMenu = this._createSnippetsMenuInstance(options);
            await this._insertSnippetMenu();

            this._onBeforeUnload = (event) => {
                if (this.isDirty()) {
                    event.returnValue = _t('This document is not saved!');
                }
            };
            window.addEventListener('beforeunload', this._onBeforeUnload);
        }
        if (this.options.getContentEditableAreas) {
            $(this.options.getContentEditableAreas()).find('*').off('mousedown mouseup click');
        }

        // The toolbar must be configured after the snippetMenu is loaded
        // because if snippetMenu is loaded in an iframe, binding of the color
        // buttons must use the jquery loaded in that iframe. See
        // _createPalette.
        this._configureToolbar(options);

        $(this.odooEditor.editable).on('mouseup', this._updateEditorUI.bind(this));
        $(this.odooEditor.editable).on('keydown', this._updateEditorUI.bind(this));
        $(this.odooEditor.editable).on('keydown', this._handleShortcuts.bind(this));
        // Ensure the Toolbar always have the correct layout in note.
        this._updateEditorUI();

        this.$root.on('click', (ev) => {
            const $target = $(ev.target).closest('a');

            // Keep popover open if clicked inside it, but not on a button
            if ($(ev.target).parents('.o_edit_menu_popover').length && !$target.length) {
                ev.preventDefault();
            }

            if ($target.is(this.customizableLinksSelector)
                    && $target.is('a')
                    && $target[0].isContentEditable
                    && !$target.attr('data-oe-model')
                    && !$target.find('> [data-oe-model]').length
                    && !$target[0].closest('.o_extra_menu_items')
                    && $target[0].isContentEditable) {
                if (ev.ctrlKey || ev.metaKey) {
                    window.open(ev.target.href, '_blank')
                }
                this.linkPopover = $target.data('popover-widget-initialized');
                if (!this.linkPopover) {
                    // TODO this code is ugly maybe the mutex should be in the
                    // editor root widget / the popover should not depend on
                    // editor panel (like originally intended but...) / ...
                    (async () => {
                        let container;
                        if (this.snippetsMenu) {
                            // Await for the editor panel to be fully updated
                            // as some buttons of the link popover we create
                            // here relies on clicking in that editor panel...
                            await this.snippetsMenu._mutex.exec(() => null);
                            container = this.options.document.getElementById('oe_manipulators');
                        }
                        this.linkPopover = await weWidgets.LinkPopoverWidget.createFor(this, $target[0], { wysiwyg: this, container });
                        $target.data('popover-widget-initialized', this.linkPopover);
                    })();
                }
                // Setting the focus on the closest contenteditable element
                // resets the selection inside that element if no selection
                // exists.
                $target.closest('[contenteditable=true]').focus();
                if ($target.closest('#wrapwrap').length && this.snippetsMenu) {
                    this.toggleLinkTools({
                        forceOpen: true,
                        link: $target[0],
                        noFocusUrl: ev.detail === 1,
                    });
                }
            }
        });

        this._onSelectionChange = this._onSelectionChange.bind(this);
        this.odooEditor.document.addEventListener('selectionchange', this._onSelectionChange);
        this.setCSSVariables(this.snippetsMenu ? this.snippetsMenu.el : this.toolbar.el);

        this.odooEditor.addEventListener('preObserverActive', () => {
            // The setONotEditable will be called right after the
            // editor sanitization (to be right before the historyStep).
            // If any `.o_not_editable` is created while the observer is
            // unactive, now is the time to call `setONotEditable` before the
            // editor could register a mutation.
            this._setONotEditable(this.odooEditor.editable);
        });

        if (this.options.autohideToolbar) {
            if (this.odooEditor.isMobile) {
                $(this.odooEditor.editable).before(this.toolbar.$el);
            } else {
                $(document.body).append(this.toolbar.$el);
            }
        }
    },
    setupCollaboration(collaborationChannel) {
        const modelName = collaborationChannel.collaborationModelName;
        const fieldName = collaborationChannel.collaborationFieldName;
        const resId = collaborationChannel.collaborationResId;
        const channelName = `editor_collaboration:${modelName}:${fieldName}:${resId}`;

        if (
            !(modelName && fieldName && resId) ||
            Wysiwyg.activeCollaborationChannelNames.has(channelName)
        ) {
            return;
        }

        this._collaborationChannelName = channelName;
        this._historyStepsBuffer = [];
        Wysiwyg.activeCollaborationChannelNames.add(channelName);

        const collaborationBusListener = ({ detail: notifications}) => {
            for (const { payload, type } of notifications) {
                if (
                    type === 'editor_collaboration' &&
                    payload.model_name === modelName &&
                    payload.field_name === fieldName &&
                    payload.res_id === resId
                ) {
                    if (payload.notificationName === 'html_field_write') {
                        this._onServerLastIdUpdate(payload.notificationPayload.last_step_id);
                    } else if (this._ptpJoined) {
                        this._peerToPeerLoading.then(() => this.ptp.handleNotification(payload));
                    }
                }
            }
        }
        this.call('bus_service', 'addEventListener', 'notification', collaborationBusListener);
        this.call('bus_service', 'addChannel', this._collaborationChannelName);
        this._collaborationStopBus = () => {
            Wysiwyg.activeCollaborationChannelNames.delete(this._collaborationChannelName);
            this.call('bus_service', 'removeEventListener', 'notification', collaborationBusListener);
            this.call('bus_service', 'deleteChannel', this._collaborationChannelName);
        }

        this._startCollaborationTime = new Date().getTime();

        this._checkConnectionChange = () => {
            if (!this.ptp) {
                return;
            }
            if (!navigator.onLine) {
                this._signalOffline();
            } else {
                this._signalOnline();
            }
        };

        window.addEventListener('online', this._checkConnectionChange);
        window.addEventListener('offline', this._checkConnectionChange);

        this._collaborationInterval = setInterval(async () => {
            if (this._offlineTimeout || this.preSavePromise || !this.ptp) {
                return;
            }

            const clientsInfos = Object.values(this.ptp.clientsInfos);
            const couldBeDisconnected =
                Boolean(clientsInfos.length) &&
                clientsInfos.every((x) => PTP_CLIENT_DISCONNECTED_STATES.includes(x.peerConnection && x.peerConnection.connectionState));

            if (couldBeDisconnected) {
                this._offlineTimeout = setTimeout(() => {
                    this._signalOffline();
                }, CONSIDER_OFFLINE_TIME);
            }
        }, CHECK_OFFLINE_TIME);

        this._peerToPeerLoading = new Promise(async (resolve) => {
            if (!ICE_SERVERS) {
                ICE_SERVERS = await this._rpc({route: '/web_editor/get_ice_servers'});
            }
            let iceServers = ICE_SERVERS;
            if (!iceServers.length) {
                iceServers = [
                    {
                        urls: [
                            'stun:stun1.l.google.com:19302',
                            'stun:stun2.l.google.com:19302',
                        ],
                    }
                ];
            }
            this._iceServers = iceServers;

            this.ptp = this._getNewPtp();

            resolve();
        });

        const editorCollaborationOptions = {
            collaborationClientId: this._currentClientId,
            onHistoryStep: (historyStep) => {
                if (!this.ptp) return;
                this.ptp.notifyAllClients('oe_history_step', historyStep, { transport: 'rtc' });
            },
            onCollaborativeSelectionChange: _.throttle((collaborativeSelection) => {
                if (!this.ptp) return;
                this.ptp.notifyAllClients('oe_history_set_selection', collaborativeSelection, { transport: 'rtc' });
            }, 50),
            onHistoryMissingParentSteps: async ({ step, fromStepId }) => {
                if (!this.ptp) return;
                const missingSteps = await this.requestClient(
                    step.clientId,
                    'get_missing_steps', {
                        fromStepId: fromStepId,
                        toStepId: step.id
                    },
                    { transport: 'rtc' }
                );
                if (missingSteps === REQUEST_ERROR) return;
                this._processMissingSteps(Array.isArray(missingSteps) ? missingSteps.concat(step) : missingSteps);
            },
        };
        return editorCollaborationOptions;
    },
    /**
     * @override
     */
    destroy: function () {
        Wysiwyg.activeWysiwygs.delete(this);

        this._stopPeerToPeer();
        document.removeEventListener("mousemove", this._signalOnline, true);
        document.removeEventListener("keydown", this._signalOnline, true);
        document.removeEventListener("keyup", this._signalOnline, true);
        this._collaborationStopBus && this._collaborationStopBus();
        if (this.odooEditor) {
            this.odooEditor.document.removeEventListener("mousemove", this._signalOnline, true);
            this.odooEditor.document.removeEventListener("keydown", this._signalOnline, true);
            this.odooEditor.document.removeEventListener("keyup", this._signalOnline, true);
            this.odooEditor.document.removeEventListener('selectionchange', this._onSelectionChange);
            for (const observer of this._oNotEditableObservers.values()) {
                observer.disconnect();
            }
            this.odooEditor.destroy();
        }
        // If peer to peer is initializing, wait for properly closing it.
        if (this._peerToPeerLoading) {
            this._peerToPeerLoading.then(()=> {
                this._stopPeerToPeer();
                this._collaborationStopBus && this._collaborationStopBus();
            });
        }
        clearInterval(this._collaborationInterval);
        this.$editable && this.$editable.off('blur', this._onBlur);
        document.removeEventListener('mousedown', this._onDocumentMousedown, true);
        const $body = $(document.body);
        $body.off('mousemove', this.resizerMousemove);
        $body.off('mouseup', this.resizerMouseup);
        const $wrapwrap = $('#wrapwrap');
        if ($wrapwrap.length) {
            $('#wrapwrap')[0].removeEventListener('scroll', this.odooEditor.multiselectionRefresh, { passive: true });
        }
        $(this.$root).off('click');
        if (this.linkPopover) {
            this.linkPopover.hide();
        }
        if (this._checkConnectionChange) {
            window.removeEventListener('online', this._checkConnectionChange);
            window.removeEventListener('offline', this._checkConnectionChange);
        }
        window.removeEventListener('beforeunload', this._onBeforeUnload);
        for (const timeout of this.tooltipTimeouts) {
            clearTimeout(timeout);
        }
        snippetsOptions.clearM2oRpcCache();
        document.removeEventListener('scroll', this._onScroll, true);
        this._super();
    },
    /**
     * @override
     */
    renderElement: function () {
        this.$editable = this.options.editable || $('<div class="note-editable">');

        // We add the field's name as id so default_focus will target it if
        // needed. For that to work, it has to already be editable but note that
        // the editor is at this point not yet instantiated.
        if (typeof this.options.fieldId !== 'undefined' && !this.options.inIframe) {
            this.$editable.attr('id', this.options.fieldId);
            this.$editable.attr('contenteditable', true);
        }

        this.$root = this.$editable;
        if (this.options.height) {
            this.$editable.height(this.options.height);
        }
        if (this.options.minHeight) {
            this.$editable.css('min-height', this.options.minHeight);
        }
        if (this.options.maxHeight && this.options.maxHeight > 10) {
            this.$editable.css('max-height', this.options.maxHeight);
        }
        if (this.options.resizable && !device.isMobile) {
            const $wrapper = $('<div class="o_wysiwyg_wrapper odoo-editor">');
            this.$root = $wrapper;
            $wrapper.append(this.$editable);
            this.$resizer = $(`<div class="o_wysiwyg_resizer">
                <div class="o_wysiwyg_resizer_hook"></div>
                <div class="o_wysiwyg_resizer_hook"></div>
                <div class="o_wysiwyg_resizer_hook"></div>
            </div>`);
            $wrapper.append(this.$resizer);
            this._replaceElement($wrapper);

            const minHeight = this.options.minHeight || 100;
            this.$editable.height(this.options.height || minHeight);

            // resizer hooks
            let startOffsetTop;
            let startHeight;
            const $body = $(document.body);
            const resizerMousedown = (e) => {
                e.preventDefault();
                e.stopPropagation();
                $body.on('mousemove', this.resizerMousemove);
                $body.on('mouseup', this.resizerMouseup);
                startHeight = this.$editable.height();
                startOffsetTop = e.pageY;
            };
            this.resizerMousemove = (e) => {
                const offsetTop = e.pageY - startOffsetTop;
                let height = startHeight + offsetTop;
                if (height < minHeight) {
                    height = minHeight;
                }
                this.$editable.height(height);
            };
            this.resizerMouseup = () => {
                $body.off('mousemove', this.resizerMousemove);
                $body.off('mouseup', this.resizerMouseup);
            };
            this.$resizer.on('mousedown', resizerMousedown);
        } else {
            if (this.options.sideAttach) {
                return this._super(...arguments);
            } else {
                this._replaceElement(this.$editable);
            }
        }
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Return the editable area.
     *
     * @returns {jQuery}
     */
    getEditable: function () {
        return this.$editable;
    },
    /**
     * Return true if the content has changed.
     *
     * @returns {Boolean}
     */
    isDirty: function () {
        const isDocumentDirty = this.$editable[0].ownerDocument.defaultView.$(".o_dirty").length;
        return this._initialValue !== (this.getValue() || this.$editable.val()) && isDocumentDirty;
    },
    /**
     * Get the value of the editable element.
     *
     * @param {object} [options]
     * @param {jQuery} [options.$layout]
     * @returns {String}
     */
    getValue: function (options) {
        var $editable = options && options.$layout || this.$editable.clone();
        $editable.find('[contenteditable]').removeAttr('contenteditable');
        $editable.find('[class=""]').removeAttr('class');
        $editable.find('[style=""]').removeAttr('style');
        $editable.find('[title=""]').removeAttr('title');
        $editable.find('[alt=""]').removeAttr('alt');
        $editable.find('[data-bs-original-title=""]').removeAttr('data-bs-original-title');
        $editable.find('[data-editor-message]').removeAttr('data-editor-message');
        $editable.find('a.o_image, span.fa, i.fa').html('');
        $editable.find('[aria-describedby]').removeAttr('aria-describedby').removeAttr('data-bs-original-title');
        this.odooEditor && this.odooEditor.cleanForSave($editable[0]);
        this._attachHistoryIds($editable[0]);
        return $editable.html();
    },
    /**
     * Save the content in the target
     *      - in init option beforeSave
     *      - receive editable jQuery DOM as attribute
     *      - called after deactivate codeview if needed
     * @returns {Promise}
     *      - resolve with true if the content was dirty
     */
    save: function () {
        const isDirty = this.isDirty();
        const html = this.getValue();
        if (this.$editable.is('textarea')) {
            this.$editable.val(html);
        } else {
            this.$editable.html(html);
        }
        return Promise.resolve({isDirty: isDirty, html: html});
    },
    /**
     * Reset the history.
     */
    historyReset: function () {
        this.odooEditor.historyReset();
    },
    /**
     * Saves the content.
     *
     * @param {boolean} [reload=true]
     * @returns {Promise}
     */
    saveContent: async function (reload = true) {
        // TODO dead code: we await for nothing. But let's be extra careful and
        // only remove it in master as `await nothing` actually allows external
        // code to take over before the rest of the function here is executed.
        const defs = [];
        await Promise.all(defs);

        this.savingContent = true;
        await this.cleanForSave();

        const editables = this.options.getContentEditableAreas();
        await this.saveModifiedImages(editables.length ? $(editables) : this.$editable);
        await this._saveViewBlocks();
        this.savingContent = false;

        window.removeEventListener('beforeunload', this._onBeforeUnload);
        if (reload) {
            window.location.reload();
        }
    },
    /**
     * Checks if the Wysiwyg is currently saving content. It can be used to
     * prevent some unwanted actions during save.
     *
     * @returns {Boolean}
     */
    isSaving() {
        return !!this.savingContent;
    },
    /**
     * Asks the user if he really wants to discard its changes (if there are
     * some of them), then simply reload the page if he wants to.
     *
     * @param {boolean} [reload=true]
     *        true if the page has to be reloaded when the user answers yes
     *        (do nothing otherwise but add this to allow class extension)
     * @returns {Promise}
     */
    cancel: function (reload) {
        var self = this;
        return new Promise((resolve, reject) => {
            if (!this.odooEditor.historySize().length) {
                resolve();
            } else {
                var confirm = Dialog.confirm(this, _t("If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."), {
                    confirm_callback: resolve,
                });
                confirm.on('closed', self, reject);
            }
        }).then(function () {
            if (reload !== false) {
                window.onbeforeunload = null;
                return self._reload();
            }
        });
    },
    /**
     * Create/Update cropped attachments.
     *
     * @param {jQuery} $editable
     * @returns {Promise}
     */
    saveModifiedImages: function ($editable = this.$editable) {
        const defs = _.map($editable, async editableEl => {
            const { resModel, resId } = this._getRecordInfo(editableEl);
            const proms = [...editableEl.querySelectorAll('.o_modified_image_to_save')].map(async el => {
                const isBackground = !el.matches('img');
                const dirtyEditable = el.closest(".o_dirty");
                if (dirtyEditable && dirtyEditable !== editableEl) {
                    // Do nothing as there is an editableEl closer to the image
                    // that will perform the rpc call with the correct model and
                    // id parameters.
                    return;
                }
                // Modifying an image always creates a copy of the original, even if
                // it was modified previously, as the other modified image may be used
                // elsewhere if the snippet was duplicated or was saved as a custom one.
                const newAttachmentSrc = await this._rpc({
                    route: `/web_editor/modify_image/${encodeURIComponent(el.dataset.originalId)}`,
                    params: {
                        res_model: resModel,
                        res_id: parseInt(resId),
                        data: (isBackground ? el.dataset.bgSrc : el.getAttribute('src')).split(',')[1],
                        mimetype: el.dataset.mimetype,
                        name: (el.dataset.fileName ? el.dataset.fileName : null),
                    },
                });
                el.classList.remove('o_modified_image_to_save');
                if (isBackground) {
                    const parts = weUtils.backgroundImageCssToParts($(el).css('background-image'));
                    parts.url = `url('${newAttachmentSrc}')`;
                    const combined = weUtils.backgroundImagePartsToCss(parts);
                    $(el).css('background-image', combined);
                    delete el.dataset.bgSrc;
                } else {
                    el.setAttribute('src', newAttachmentSrc);
                }
            });
            return Promise.all(proms);
        });
        return Promise.all(defs);
    },
    /**
     * @param {String} value
     * @returns {String}
     */
    setValue: function (value) {
        this.odooEditor.resetContent(value);
    },
    /**
     * Undo one step of change in the editor.
     */
    undo: function () {
        this.odooEditor.historyUndo();
    },
    /**
     * Redo one step of change in the editor.
     */
    redo: function () {
        this.odooEditor.historyRedo();
    },
    /**
     * Focus inside the editor.
     *
     * Set cursor to the editor latest position before blur or to the last editable node, ready to type.
     */
    focus: function () {
        if (this.odooEditor && !this.odooEditor.historyResetLatestComputedSelection(true)) {
            // If the editor don't have an history step to focus to,
            // We place the cursor after the end of the editor exiting content.
            const range = document.createRange();
            const elementToTarget = this.$editable[0].lastElementChild ? this.$editable[0].lastElementChild : this.$editable[0];
            range.selectNodeContents(elementToTarget);
            range.collapse();

            const selection = this.odooEditor.document.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
        }
    },
    getDeepRange() {
        return getDeepRange(this.odooEditor.editable);
    },
    closestElement(...args) {
        return closestElement(...args);
    },
    async cleanForSave() {
        if (this.odooEditor) {
            this.odooEditor.cleanForSave();
            this._attachHistoryIds();
        }

        if (this.snippetsMenu) {
            await this.snippetsMenu.cleanForSave();
        }
    },
    isSelectionInEditable: function () {
        return this.odooEditor.isSelectionInEditable();
    },
    /**
     * Start or resume the Odoo field changes muation observers.
     *
     * Necessary to keep all copies of a given field at the same value throughout the page.
     */
    _observeOdooFieldChanges: function () {
        const observerOptions = {
            childList: true,
            subtree: true,
            attributes: true,
            characterData: true,
            attributeOldValue: true,
        };
        if (this.odooFieldObservers) {
            for (let observerData of this.odooFieldObservers) {
                observerData.observer.observe(observerData.field, observerOptions);
            }
        } else {
            const odooFieldSelector = '[data-oe-model], [data-oe-translation-initial-sha]';
            const $odooFields = this.$editable.find(odooFieldSelector);
            this.odooFieldObservers = [];

            $odooFields.each((i, field) => {
                const observer = new MutationObserver((mutations) => {
                    mutations = this.odooEditor.filterMutationRecords(mutations);
                    if (!mutations.length) {
                        return;
                    }
                    let $node = $(field);
                    // Do not forward "unstyled" copies to other nodes.
                    if ($node.hasClass('o_translation_without_style')) {
                        return;
                    }
                    let $nodes = $odooFields.filter(function () {
                        return this !== field;
                    });
                    if ($node.data('oe-model')) {
                        $nodes = $nodes.filter('[data-oe-model="' + $node.data('oe-model') + '"]')
                            .filter('[data-oe-id="' + $node.data('oe-id') + '"]')
                            .filter('[data-oe-field="' + $node.data('oe-field') + '"]');
                    }

                    if ($node.data('oe-translation-initial-sha')) {
                        $nodes = $nodes.filter('[data-oe-translation-initial-sha="' + $node.data('oe-translation-initial-sha') + '"]');
                    }
                    if ($node.data('oe-type')) {
                        $nodes = $nodes.filter('[data-oe-type="' + $node.data('oe-type') + '"]');
                    }
                    if ($node.data('oe-expression')) {
                        $nodes = $nodes.filter('[data-oe-expression="' + $node.data('oe-expression') + '"]');
                    } else if ($node.data('oe-xpath')) {
                        $nodes = $nodes.filter('[data-oe-xpath="' + $node.data('oe-xpath') + '"]');
                    }
                    if ($node.data('oe-contact-options')) {
                        $nodes = $nodes.filter("[data-oe-contact-options='" + $node[0].dataset.oeContactOptions + "']");
                    }

                    let nodes = $node.get();

                    if ($node.data('oe-type') === "many2one") {
                        $nodes = $nodes.add($('[data-oe-model]')
                            .filter(function () {
                                return this !== $node[0] && nodes.indexOf(this) === -1;
                            })
                            .filter('[data-oe-many2one-model="' + $node.data('oe-many2one-model') + '"]')
                            .filter('[data-oe-many2one-id="' + $node.data('oe-many2one-id') + '"]')
                            .filter('[data-oe-type="many2one"]'));

                        $nodes = $nodes.add($('[data-oe-model]')
                            .filter(function () {
                                return this !== $node[0] && nodes.indexOf(this) === -1;
                            })
                            .filter('[data-oe-model="' + $node.data('oe-many2one-model') + '"]')
                            .filter('[data-oe-id="' + $node.data('oe-many2one-id') + '"]')
                            .filter('[data-oe-field="name"]'));
                    }

                    this._pauseOdooFieldObservers();
                    // Tag the date fields to only replace the value
                    // with the original date value once (see mouseDown event)
                    if ($node.hasClass('o_editable_date_field_format_changed')) {
                        $nodes.addClass('o_editable_date_field_format_changed');
                    }
                    const html = $node.html();
                    for (const node of $nodes) {
                        if (node.classList.contains('o_translation_without_style')) {
                            // For generated elements such as the navigation
                            // labels of website's table of content, only the
                            // text of the referenced translation must be used.
                            const text = $node.text();
                            if (node.innerText !== text) {
                                node.innerText = text;
                            }
                            continue;
                        }
                        if (node.innerHTML !== html) {
                            node.innerHTML = html;
                        }
                    }
                    this._observeOdooFieldChanges();
                });
                observer.observe(field, observerOptions);
                this.odooFieldObservers.push({field: field, observer: observer});
            });
        }
    },
    /**
     * Stop the field changes mutation observers.
     */
    _pauseOdooFieldObservers: function () {
        for (let observerData of this.odooFieldObservers) {
            observerData.observer.disconnect();
        }
    },
    /**
     * Open the link tools or the image link tool depending on the selection.
     */
    openLinkToolsFromSelection() {
        const targetEl = this.odooEditor.document.getSelection().getRangeAt(0).startContainer;
        // Link tool is different if the selection is an image or a text.
        if (targetEl.nodeType === Node.ELEMENT_NODE
                && (targetEl.tagName === 'IMG' || targetEl.querySelectorAll('img').length === 1)) {
            core.bus.trigger('activate_image_link_tool');
            return;
        }
        this.toggleLinkTools();
    },
    /**
     * Toggle the Link tools/dialog to edit links. If a snippet menu is present,
     * use the link tools, otherwise use the dialog.
     *
     * @param {boolean} [options.forceOpen] default: false
     * @param {boolean} [options.forceDialog] force to open the dialog
     * @param {boolean} [options.link] The anchor element to edit if it is known.
     * @param {boolean} [options.noFocusUrl=false] Disable the automatic focusing of the URL field.
     */
    toggleLinkTools(options = {}) {
        const linkEl = getInSelection(this.odooEditor.document, 'a');
        if (linkEl && (!linkEl.matches(this.customizableLinksSelector) || !linkEl.isContentEditable)) {
            return;
        }
        if (this.snippetsMenu && !options.forceDialog) {
            if (options.link && options.link.querySelector(mediaSelector) &&
                    !options.link.textContent.trim() && wysiwygUtils.isImg(this.lastElement)) {
                // If the link contains a media without text, the link is
                // editable in the media options instead.
                if (!options.noFocusUrl) {
                    // Wait for the editor panel to be fully updated.
                    this.snippetsMenu._mutex.exec(() => {
                        // This is needed to focus the URL input when clicking
                        // on the "Edit link" of the popover.
                        core.bus.trigger('activate_image_link_tool');
                    });
                }
                return;
            }
            if (options.forceOpen || !this.linkTools) {
                const $btn = this.toolbar.$el.find('#create-link');
                if (!this.linkTools || ![options.link, ...wysiwygUtils.ancestors(options.link)].includes(this.linkTools.$link[0])) {
                    const { link } = Link.getOrCreateLink({
                        containerNode: this.odooEditor.editable,
                        startNode: options.link || this.lastMediaClicked,
                    });
                    if (!link) {
                        return
                    }
                    const linkToolsData = Object.assign({}, this.options.defaultDataForLinkTools);
                    this.linkTools = new weWidgets.LinkTools(this, {wysiwyg: this, noFocusUrl: options.noFocusUrl}, this.odooEditor.editable, linkToolsData, $btn, link );
                }
                this.linkTools.noFocusUrl = options.noFocusUrl;
                const _onClick = ev => {
                    if (
                        !ev.target.closest('#create-link') &&
                        (!ev.target.closest('.oe-toolbar') || !ev.target.closest('we-customizeblock-option')) &&
                        !ev.target.closest('.ui-autocomplete') &&
                        (!this.linkTools || ![ev.target, ...wysiwygUtils.ancestors(ev.target)].includes(this.linkTools.$link[0]))
                    ) {
                        // Destroy the link tools on click anywhere outside the
                        // toolbar if the target is the orgiginal target not in the original target.
                        this.destroyLinkTools();
                        this.odooEditor.document.removeEventListener('click', _onClick, true);
                        document.removeEventListener('click', _onClick, true);
                    }
                };
                this.odooEditor.document.addEventListener('click', _onClick, true);
                document.addEventListener('click', _onClick, true);
                if (!this.linkTools.$el) {
                    this.linkTools.appendTo(this.toolbar.$el);
                }
            } else {
                this.destroyLinkTools();
            }
        } else {
            const historyStepIndex = this.odooEditor.historySize() - 1;
            this.odooEditor.historyPauseSteps();
            let { link } = Link.getOrCreateLink({
                containerNode: this.odooEditor.editable,
                startNode: options.link,
            });
            if (!link) {
                return
            }
            const linkDialog = new weWidgets.LinkDialog(this, {
                forceNewWindow: this.options.linkForceNewWindow,
                wysiwyg: this,
                focusField: link.innerHTML ? 'url' : '',
            }, this.$editable[0], {
                needLabel: true
            }, undefined, link);
            this._shouldDelayBlur = true;
            linkDialog.open();
            linkDialog.on('save', this, data => {
                if (!data) {
                    return;
                }
                const linkWidget = linkDialog.linkWidget;
                getDeepRange(this.$editable[0], {range: data.range, select: true});
                if (this.options.userGeneratedContent) {
                    data.rel = 'ugc';
                }
                linkWidget.applyLinkToDom(data);
                this.odooEditor.historyUnpauseSteps();
                this.odooEditor.historyStep();
                link = linkWidget.$link[0];
                setSelection(link, 0, link, link.childNodes.length, false);
                // Focus the link after the dialog element is removed because
                // if the dialog element is still in the DOM at the time of
                // doing link.focus(), because there is the attribute tabindex
                // on the dialog element, the focus cannot occur.
                // Using a microtask to set the focus is hackish and might break
                // if another microtask which focuses an element in the dom
                // occurs at the same time (but this case seems unlikely).
                Promise.resolve().then(() => link.focus());
            });
            linkDialog.on('closed', this, function () {
                this.odooEditor.historyUnpauseSteps();
                // If the linkDialog content has been saved
                // the previous selection in not relevant anymore.
                if (linkDialog.destroyAction !== 'save') {
                    // Restore the selection after the dialog element isremoved
                    // because if the dialog element is still in the DOM at the
                    // time of doing restoreSelection(), it will trigger a new
                    // selection change which will undo this one. Using a
                    // microtask to set the focus is hackish and might break if
                    // another microtask which changes the selection in the dom
                    // occurs at the same time (but this case seems unlikely).
                    Promise.resolve().then(() => this.odooEditor.historyRevertUntil(historyStepIndex));
                }
            });
        }
    },
    /**
     * Removes the current Link.
     */
    removeLink() {
        if (this.snippetsMenu && wysiwygUtils.isImg(this.lastElement)) {
            this.snippetsMenu._mutex.exec(() => {
                // Wait for the editor panel to be fully updated.
                core.bus.trigger('deactivate_image_link_tool');
            });
        } else {
            this.odooEditor.execCommand('unlink');
        }
    },
    /**
     * Destroy the Link tools/dialog and restore the selection.
     */
    destroyLinkTools() {
        if (this.linkTools) {
            const selection = this.odooEditor.document.getSelection();
            const link = this.linkTools.$link[0];
            let anchorNode
            let focusNode;
            let anchorOffset = 0;
            let focusOffset;
            if (selection && link.parentElement) {
                // Focus the link after the dialog element is removed.
                if (this.linkTools.shouldUnlink()) {
                    if (link.childNodes.length) {
                        anchorNode = link.childNodes[0];
                        focusNode = link.childNodes[link.childNodes.length - 1];
                    } else {
                        const parent = link.parentElement;
                        const index = Array.from(parent.childNodes).indexOf(link);
                        anchorNode = focusNode = parent;
                        anchorOffset = focusOffset = index;
                    }
                } else {
                    anchorNode = link;
                    focusNode = link;
                }
                if (!focusOffset) {
                    focusOffset = focusNode.childNodes.length || focusNode.length;
                }
            }
            this.linkTools.destroy();
            if (anchorNode) {
                setSelection(anchorNode, anchorOffset, focusNode, focusOffset, false);
            }
            this.linkTools = undefined;
        }
    },
    /**
     * Open the media dialog.
     *
     * Used to insert or change image, icon, document and video.
     *
     * @param {object} params
     * @param {Node} [params.node] Optionnal
     * @param {Node} [params.htmlClass] Optionnal
     */
    openMediaDialog(params = {}) {
        const sel = this.odooEditor.document.getSelection();

        if (!sel.rangeCount) {
            return;
        }
        const range = sel.getRangeAt(0);
        // We lose the current selection inside the content editable when we
        // click the media dialog button so we need to be able to restore the
        // selection when the modal is closed.
        const restoreSelection = preserveCursor(this.odooEditor.document);

        const editable = OdooEditorLib.closestElement(range.startContainer, '.o_editable') || this.odooEditor.editable;
        const {resModel, resId, field, type } = this._getRecordInfo(editable);

        this.mediaDialogWrapper = new ComponentWrapper(this, MediaDialogWrapper, {
            resModel,
            resId,
            useMediaLibrary: !!(field && (resModel === 'ir.ui.view' && field === 'arch' || type === 'html')),
            media: params.node,
            save: this._onMediaDialogSave.bind(this, {
                node: params.node,
                restoreSelection: restoreSelection,
            }),
            onAttachmentChange: this._onAttachmentChange.bind(this),
            close: () => restoreSelection(),
            ...this.options.mediaModalParams,
            ...params,
        });

        // The wysiwyg can be instanciated inside an iframe. The dialog
        // component is mounted on the global document.
        return this.mediaDialogWrapper.mount(document.body);
    },
    /**
     * Sets custom CSS Variables on the snippet menu element.
     * Used for color previews and color palette to get the color
     * values of the editable. (e.g. if the editable is in an iframe
     * with different SCSS color values as the top window.)
     *
     * @param {HTMLElement} element
     */
    setCSSVariables(element) {
        const stylesToCopy = weUtils.EDITOR_COLOR_CSS_VARIABLES;

        for (const style of stylesToCopy) {
            element.style.setProperty(`--we-cp-${style}`, weUtils.getCSSVariableValue(style));
        }

        element.classList.toggle('o_we_has_btn_outline_primary',
            weUtils.getCSSVariableValue('btn-primary-outline') === 'true');
        element.classList.toggle('o_we_has_btn_outline_secondary',
            weUtils.getCSSVariableValue('btn-secondary-outline') === 'true');
    },
    /**
     * Detached function to allow overriding.
     *
     * @param {Object} params binded @see openMediaDialog
     * @param {Element} element provided by the dialog
     */
    _onMediaDialogSave: function (params, element) {
        params.restoreSelection();
        if (!element) {
            return;
        }

        if (params.node) {
            const isIcon = (el) => el.matches('i.fa, span.fa');
            const changedIcon = isIcon(params.node) && isIcon(element);
            if (changedIcon) {
                // Preserve tag name when changing an icon and not recreate the
                // editors unnecessarily.
                for (const attribute of element.attributes) {
                    params.node.setAttribute(attribute.nodeName, attribute.nodeValue);
                }
            } else {
                params.node.replaceWith(element);
            }
            this.odooEditor.unbreakableStepUnactive();
            this.odooEditor.historyStep();
        } else {
            return this.odooEditor.execCommand('insert', element);
        }

        if (this.snippetsMenu) {
            this.snippetsMenu.activateSnippet($(element)).then(() => {
                if (element.tagName === 'IMG') {
                    $(element).trigger('image_changed');
                }
            });
        }
    },
    getInSelection(selector) {
        return getInSelection(this.odooEditor.document, selector);
    },
    /**
     * Adds an empty action in the mutex. Can be used to wait for some options
     * to be initialized before doing something else.
     *
     * @returns {Promise}
     */
    waitForEmptyMutexAction() {
        if (this.snippetsMenu) {
            return this.snippetsMenu.execWithLoadingEffect(() => null, false);
        }
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getRecordInfo() {
        const { res_model: resModel, res_id: resId } = this.options.recordInfo;
        return { resModel, resId };
    },
    /**
     * Returns an instance of the snippets menu.
     *
     * @param {Object} [options]
     * @returns {widget}
     */
    _createSnippetsMenuInstance: function (options={}) {
        return new snippetsEditor.SnippetsMenu(this, Object.assign({
            wysiwyg: this,
            selectorEditableArea: '.o_editable',
        }, options));
    },
    _configureToolbar: function (options) {
        const $toolbar = this.toolbar.$el;
        // Prevent selection loss when interacting with the toolbar buttons.
        $toolbar.find('.btn-group').on('mousedown', e => {
            if (
                // Prevent when clicking on btn-group but not on dropdown items.
                !e.target.closest('.dropdown-menu') ||
                // Unless they have a data-call in which case there is an editor
                // command that is bound to it so we need to preventDefault.
                e.target.closest('.btn') && e.target.closest('.btn').getAttribute('data-call')
            ) {
                e.preventDefault();
            }
        });
        const openTools = e => {
            e.preventDefault();
            e.stopImmediatePropagation();
            e.stopPropagation();
            switch (e.target.id) {
                case 'create-link':
                    this.toggleLinkTools();
                    break;
                case 'media-insert':
                case 'media-replace':
                    this.openMediaDialog({ node: this.lastMediaClicked });
                    break;
                case 'media-description':
                    new weWidgets.AltDialog(this, {}, this.lastMediaClicked).open();
                    break;
            }
        };
        if (!options.snippets) {
            $toolbar.find('#justify, #table, #media-insert').remove();
        }
        $toolbar.find('#media-insert, #media-replace, #media-description').click(openTools);
        $toolbar.find('#create-link').click(openTools);
        $toolbar.find('#image-shape div, #fa-spin').click(e => {
            if (!this.lastMediaClicked) {
                return;
            }
            this.lastMediaClicked.classList.toggle(e.target.id);
            e.target.classList.toggle('active', $(this.lastMediaClicked).hasClass(e.target.id));
        });
        const $imageWidthButtons = $toolbar.find('#image-width div');
        $imageWidthButtons.click(e => {
            if (!this.lastMediaClicked) {
                return;
            }
            this.lastMediaClicked.style.width = e.target.id;
            for (const button of $imageWidthButtons) {
                button.classList.toggle('active', this.lastMediaClicked.style.width === button.id);
            }
        });
        $toolbar.find('#image-padding .dropdown-item').click(e => {
            if (!this.lastMediaClicked) {
                return;
            }
            $(this.lastMediaClicked).removeClass((index, className) => (
                (className.match(/(^|\s)padding-\w+/g) || []).join(' ')
            )).addClass(e.target.dataset.class);
        });
        $toolbar.on('mousedown', e => {
            const justifyBtn = e.target.closest('#justify div.btn');
            if (!justifyBtn || !this.lastMediaClicked) {
                return;
            }
            e.originalEvent.stopImmediatePropagation();
            e.originalEvent.stopPropagation();
            e.originalEvent.preventDefault();
            const mode = justifyBtn.id.replace('justify', '').toLowerCase();
            const classes = mode === 'center' ? ['d-block', 'mx-auto'] : ['float-' + mode];
            const doAdd = classes.some(className => !this.lastMediaClicked.classList.contains(className));
            this.lastMediaClicked.classList.remove('float-start', 'float-end');
            if (this.lastMediaClicked.classList.contains('mx-auto')) {
                this.lastMediaClicked.classList.remove('d-block', 'mx-auto');
            }
            if (doAdd) {
                this.lastMediaClicked.classList.add(...classes);
            }
            this._updateMediaJustifyButton(justifyBtn.id);
        });
        $toolbar.find('#image-crop').click(e => {
            if (!this.lastMediaClicked) {
                return;
            }
            new weWidgets.ImageCropWidget(this, this.lastMediaClicked).appendTo(this.odooEditor.document.body);
            this.odooEditor.toolbarHide();
            $(this.lastMediaClicked).on('image_cropper_destroyed', () => this.odooEditor.toolbarShow());
        });
        $toolbar.find('#image-transform').click(e => {
            if (!this.lastMediaClicked) {
                return;
            }
            const $image = $(this.lastMediaClicked);
            if ($image.data('transfo-destroy')) {
                $image.removeData('transfo-destroy');
                return;
            }
            $image.transfo({document: this.odooEditor.document});
            const mouseup = () => {
                $('#image-transform').toggleClass('active', $image.is('[style*="transform"]'));
            };
            $(this.odooEditor.document).on('mouseup', mouseup);
            const mousedown = mousedownEvent => {
                if (!$(mousedownEvent.target).closest('.transfo-container').length) {
                    $image.transfo('destroy');
                    $(this.odooEditor.document).off('mousedown', mousedown).off('mouseup', mouseup);
                }
                if ($(mousedownEvent.target).closest('#image-transform').length) {
                    $image.data('transfo-destroy', true).attr('style', ($image.attr('style') || '').replace(/[^;]*transform[\w:]*;?/g, ''));
                }
                $image.trigger('content_changed');
            };
            $(this.odooEditor.document).on('mousedown', mousedown);
        });
        $toolbar.find('#image-delete').click(e => {
            if (!this.lastMediaClicked) {
                return;
            }
            $(this.lastMediaClicked).remove();
            this.lastMediaClicked = undefined;
            this.odooEditor.toolbarHide();
        });
        $toolbar.find('#fa-resize div').click(e => {
            if (!this.lastMediaClicked) {
                return;
            }
            const $target = $(this.lastMediaClicked);
            const sValue = e.target.dataset.value;
            $target.attr('class', $target.attr('class').replace(/\s*fa-[0-9]+x/g, ''));
            if (+sValue > 1) {
                $target.addClass('fa-' + sValue + 'x');
            }
            this._updateFaResizeButtons();
        });
        const $colorpickerGroup = $toolbar.find('#colorInputButtonGroup');
        if ($colorpickerGroup.length) {
            this._createPalette();
        }
        if (!options.snippets) {
            // Scroll event does not bubble.
            document.addEventListener('scroll', this._onScroll, true);
        }
    },
    /**
     * @private
     * @param {jQuery} $
     * @param {String} eventName 'foreColor' or 'backColor'
     * @returns {String} color
     */
    _getSelectedColor($, eventName) {
        const selection = this.odooEditor.document.getSelection();
        const range = selection.rangeCount && selection.getRangeAt(0);
        const targetNode = range && range.startContainer;
        const targetElement = targetNode && targetNode.nodeType === Node.ELEMENT_NODE
            ? targetNode
            : targetNode && targetNode.parentNode;
        const backgroundImage = $(targetElement).css('background-image');
        let backgroundGradient = false;
        if (weUtils.isColorGradient(backgroundImage)) {
            const textGradient = targetElement.classList.contains('text-gradient');
            if (eventName === "foreColor" && textGradient || eventName !== "foreColor" && !textGradient) {
                backgroundGradient = backgroundImage;
            }
        }
        return backgroundGradient || $(targetElement).css(eventName === "foreColor" ? 'color' : 'backgroundColor');
    },
    _createPalette() {
        const $dropdownContent = this.toolbar.$el.find('#colorInputButtonGroup .colorPalette');
        // The editor's root widget can be website or web's root widget and cannot be properly retrieved...
        for (const elem of $dropdownContent) {
            const eventName = elem.dataset.eventName;
            let colorpicker = null;
            const mutex = new concurrency.MutexedDropPrevious();
            if (!elem.ownerDocument.defaultView) {
                // In case the element is not in the DOM, don't do anything with it.
                continue;
            }
            // If the element is within an iframe, access the jquery loaded in
            // the iframe because it is the one who will trigger the dropdown
            // events (i.e hide.bs.dropdown and show.bs.dropdown).
            const $ = elem.ownerDocument.defaultView.$;
            const $dropdown = $(elem).closest('.colorpicker-group , .dropdown');
            let manualOpening = false;
            // Prevent dropdown closing on colorpicker click
            $dropdown.on('hide.bs.dropdown', ev => {
                return !(ev.clickEvent && ev.clickEvent.__isColorpickerClick);
            });
            $dropdown.on('show.bs.dropdown', () => {
                if (manualOpening) {
                    return true;
                }
                mutex.exec(() => {
                    const oldColorpicker = colorpicker;
                    const hookEl = oldColorpicker ? oldColorpicker.el : elem;
                    const selectedColor = this._getSelectedColor($, eventName);
                    const selection = this.odooEditor.document.getSelection();
                    const range = selection.rangeCount && selection.getRangeAt(0);
                    const hadNonCollapsedSelection = range && !selection.isCollapsed;
                    // The color_leave event will revert the mutations with
                    // `historyRevertCurrentStep`. We must stash the current
                    // mutations to prevent them from being reverted.
                    this.odooEditor.historyStash();
                    colorpicker = new ColorPaletteWidget(this, {
                        excluded: ['transparent_grayscale'],
                        // TODO remove me in master: editable is just a
                        // duplicate of $editable, should be reviewed with OWL
                        // later anyway.
                        editable: this.odooEditor.editable,
                        $editable: $(this.odooEditor.editable), // Our parent is the root widget, we can't retrieve the editable section from it...
                        selectedColor: selectedColor,
                        selectedTab: weUtils.isColorGradient(selectedColor) ? 'gradients' : 'theme-colors',
                        withGradients: true,
                    });
                    this.colorpickers[eventName] = colorpicker;
                    colorpicker.on('custom_color_picked color_picked', null, ev => {
                        if (hadNonCollapsedSelection) {
                            this.odooEditor.historyResetLatestComputedSelection(true);
                        }
                        // Unstash the mutations now that the color is picked.
                        this.odooEditor.historyUnstash();
                        this._processAndApplyColor(eventName, ev.data.color);
                        // Deselect tables so the applied color can be seen
                        // without using `!important` (otherwise the selection
                        // hides it).
                        if (this.odooEditor.deselectTable() && hasValidSelection(this.odooEditor.editable)) {
                            this.odooEditor.document.getSelection().collapseToStart();
                        }
                        this._updateEditorUI(this.lastMediaClicked && { target: this.lastMediaClicked });
                        colorpicker.off('color_leave');
                    });
                    colorpicker.on('color_hover', null, ev => {
                        if (hadNonCollapsedSelection) {
                            this.odooEditor.historyResetLatestComputedSelection(true);
                        }
                        this.odooEditor.historyPauseSteps();
                        try {
                            this._processAndApplyColor(eventName, ev.data.color, true);
                        } finally {
                            this.odooEditor.historyUnpauseSteps();
                        }
                    });
                    colorpicker.on('color_leave', null, ev => {
                        this.odooEditor.historyRevertCurrentStep();
                    });
                    const $childElement = $dropdown.children('.dropdown-toggle');
                    const dropdownToggle = new Dropdown($childElement);
                    colorpicker.on('enter_key_color_colorpicker', null, () => {
                        dropdownToggle.hide();
                    });
                    return colorpicker.replace(hookEl).then(() => {
                        if (oldColorpicker) {
                            oldColorpicker.destroy();
                        }
                        manualOpening = true;
                        dropdownToggle.show();
                        const $colorpicker = $dropdown.find('.colorpicker');
                        const colorpickerHeight = $colorpicker.outerHeight();
                        const toolbarContainerTop = dom.closestScrollable(this.toolbar.el).getBoundingClientRect().top;
                        const toolbarColorButtonTop = this.toolbar.el.querySelector('#colorInputButtonGroup').getBoundingClientRect().top;
                        $dropdown[0].classList.toggle('dropup', colorpickerHeight + toolbarContainerTop <= toolbarColorButtonTop);
                        manualOpening = false;
                    });
                });
                return false;
            });
        }
    },
    _processAndApplyColor: function (eventName, color, previewMode) {
        if (color && (!ColorpickerWidget.isCSSColor(color) && !weUtils.isColorGradient(color))) {
            color = (eventName === "foreColor" ? 'text-' : 'bg-') + color;
        }
        let coloredElements = this.odooEditor.execCommand('applyColor', color, eventName === 'foreColor' ? 'color' : 'backgroundColor', this.lastMediaClicked);
        // Some nodes returned by applyColor can be removed of the document by the sanitization in historyStep
        coloredElements = coloredElements.filter(element => this.odooEditor.document.contains(element));

        const coloredTds = coloredElements && coloredElements.length && coloredElements.filter(coloredElement => coloredElement.classList.contains('o_selected_td'));
        if (coloredTds.length) {
            const propName = eventName === 'foreColor' ? 'color' : 'background-color';
            for (const td of coloredTds) {
                // Make it important so it has priority over selection color.
                td.style.setProperty(propName, td.style[propName], previewMode ? 'important' : '');
            }
        } else if (!this.lastMediaClicked && coloredElements && coloredElements.length) {
            // Ensure the selection in the fonts tags, otherwise an undetermined
            // race condition could generate a wrong selection later.
            const first = coloredElements[0];
            const last = coloredElements[coloredElements.length - 1];

            const sel = this.odooEditor.document.getSelection();
            sel.removeAllRanges();
            const range = new Range();
            range.setStart(first, 0);
            range.setEnd(...endPos(last));
            sel.addRange(range);
        }

        const hexColor = this._colorToHex(color);
        this.odooEditor.updateColorpickerLabels({
            [eventName === 'foreColor' ? 'foreColor' : 'hiliteColor']: hexColor,
        });
    },
    _colorToHex: function (color) {
        if (color.startsWith('#')) {
            return color;
        } else if (weUtils.isColorGradient(color)) {
            // return gradient the way it is: updateColorpickerLabels will handle it
            return color;
        } else {
            let rgbColor;
            if (color.startsWith('rgb')) {
                rgbColor = color;
            } else {
                const $font = $(`<font class="${color}"/>`);
                $(document.body).append($font);
                const propertyName = color.startsWith('text') ? 'color' : 'backgroundColor';
                rgbColor = $font.css(propertyName);
                $font.remove();
            }
            return rgbToHex(rgbColor);
        }
    },
    /**
     * Handle custom keyboard shortcuts.
     */
    _handleShortcuts: function (e) {
        // Open the link tool when CTRL+K is pressed.
        if (this.options.bindLinkTool && e && e.key === 'k' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            this.openLinkToolsFromSelection();
        }
        // Override selectAll (CTRL+A) to restrict it to the editable zone / current snippet and prevent traceback.
        if (e && e.key === 'a' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            const selection = this.odooEditor.document.getSelection();
            const containerSelector = '#wrap>*, .oe_structure>*, [contenteditable]';
            const container =
                (selection &&
                    closestElement(selection.anchorNode, containerSelector)) ||
                // In case a suitable container could not be found then the
                // selection is restricted inside the editable area.
                this.$editable.find(containerSelector)[0];
            if (container) {
                const range = document.createRange();
                range.selectNodeContents(container);
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }
    },
    /**
     * Update any editor UI that is not handled by the editor itself.
     */
    _updateEditorUI: function (e) {
        let selection = this.odooEditor.document.getSelection();
        const anchorNode = selection.anchorNode;
        if (anchorNode && closestElement(anchorNode, '[data-oe-protected="true"]')) {
            return;
        }

        this.odooEditor.automaticStepSkipStack();
        // Clear "d-none" for button groups.
        for (const buttonGroup of this.toolbar.el.querySelectorAll('.btn-group')) {
            buttonGroup.classList.remove('d-none');
        }
        // We need to use the editor's window so the tooltip displays in its
        // document even if it's in an iframe.
        const editorWindow = this.odooEditor.document.defaultView;
        const $target = e ? editorWindow.$(e.target) : editorWindow.$();
        // Restore paragraph dropdown button's default ID.
        this.toolbar.$el.find('#mediaParagraphDropdownButton').attr('id', 'paragraphDropdownButton');
        // Only show the media tools in the toolbar if the current selected
        // snippet is a media.
        const isInMedia = $target.is(mediaSelector) && !$target.parent().hasClass('o_stars') && e.target &&
            (e.target.isContentEditable || (e.target.parentElement && e.target.parentElement.isContentEditable));
        this.toolbar.$el.find([
            '#image-shape',
            '#image-width',
            '#image-padding',
            '#image-edit',
            '#media-replace',
        ].join(',')).toggleClass('d-none', !isInMedia);
        // The image replace button is in the image options when the sidebar
        // exists.
        if (this.snippetsMenu && !this.snippetsMenu.folded && $target.is('img')) {
            this.toolbar.$el.find('#media-replace').toggleClass('d-none', true);
        }
        // Only show the image-transform, image-crop and media-description
        // buttons if the current selected snippet is an image.
        this.toolbar.$el.find([
            '#image-transform',
            '#image-crop',
            '#media-description',
        ].join(',')).toggleClass('d-none', !$target.is('img'));
        this.lastMediaClicked = isInMedia && e.target;
        this.lastElement = $target[0];
        // Hide the irrelevant text buttons for media.
        this.toolbar.$el.find([
            '#style',
            '#decoration',
            '#font-size',
            '#justifyFull',
            '#list',
            '#colorInputButtonGroup',
            '#table',
            '#create-link',
            '#media-insert', // "Insert media" should be replaced with "Replace media".
        ].join(',')).toggleClass('d-none', isInMedia);
        // Some icons are relevant for icons, that aren't for other media.
        this.toolbar.$el.find('#colorInputButtonGroup, #create-link').toggleClass('d-none', isInMedia && !$target.is('.fa'));
        this.toolbar.$el.find('.only_fa').toggleClass('d-none', !$target.is('.fa'));
        // Hide the create-link button if the selection spans several blocks.
        selection = this.odooEditor.document.getSelection();
        const range = selection && selection.rangeCount && selection.getRangeAt(0);
        const $rangeContainer = range && $(range.commonAncestorContainer);
        const spansBlocks = range && !!$rangeContainer.contents().filter((i, node) => isBlock(node)).length;
        if (!range || spansBlocks) {
            this.toolbar.$el.find('#create-link').toggleClass('d-none', true);
        }
        // Toggle unlink button. Always hide it on media.
        const linkNode = getInSelection(this.odooEditor.document, 'a');
        const unlinkButton = this.toolbar.el.querySelector('#unlink');
        unlinkButton && unlinkButton.classList.toggle('d-none', !linkNode || isInMedia);
        // Toggle the toolbar arrow.
        this.toolbar.$el.toggleClass('noarrow', isInMedia);
        // Unselect all media.
        this.$editable.find('.o_we_selected_image').removeClass('o_we_selected_image');
        if (isInMedia) {
            this.odooEditor.automaticStepSkipStack();
            // Select the media in the DOM.
            const selection = this.odooEditor.document.getSelection();
            const range = this.odooEditor.document.createRange();
            range.selectNode(this.lastMediaClicked);
            selection.removeAllRanges();
            selection.addRange(range);
            // Toggle the 'active' class on the active image tool buttons.
            for (const button of this.toolbar.$el.find('#image-shape div, #fa-spin')) {
                button.classList.toggle('active', $(e.target).hasClass(button.id));
            }
            for (const button of this.toolbar.$el.find('#image-width div')) {
                button.classList.toggle('active', e.target.style.width === button.id);
            }
            this._updateMediaJustifyButton();
            this._updateFaResizeButtons();
        }
        if (isInMedia) {
            // Handle the media/link's tooltip.
            this.showTooltip = true;
            this.tooltipTimeouts.push(setTimeout(() => {
                // Do not show tooltip on double-click and if there is already one
                if (!this.showTooltip || $target.attr('title') !== undefined) {
                    return;
                }
                // Tooltips need to be cleared before leaving the editor.
                this.saving_mutex.exec(() => {
                    this.odooEditor.observerUnactive('tooltip');
                    $target.tooltip({title: _t('Double-click to edit'), trigger: 'manual', container: 'body'}).tooltip('show');
                    this.odooEditor.observerActive('tooltip');
                    this.tooltipTimeouts.push(setTimeout(() => $target.tooltip('dispose'), 800));
                });
            }, 400));
        }
        // Hide button groups that have no visible buttons.
        for (const buttonGroup of this.toolbar.el.querySelectorAll('.btn-group:not(.d-none)')) {
            if (!buttonGroup.querySelector('.btn:not(.d-none)')) {
                buttonGroup.classList.add('d-none');
            }
        }
        // Toolbar might have changed size, update its position.
        this.odooEditor.updateToolbarPosition();
        // Update color of already opened colorpickers.
        setTimeout(() => {
            for (let eventName in this.colorpickers) {
                const selectedColor = this._getSelectedColor($, eventName);
                if (selectedColor) {
                    // If the palette was already opened (e.g. modifying a gradient), the new DOM state
                    // must be reflected in the palette, but the tab selection must not be impacted.
                    this.colorpickers[eventName].setSelectedColor(null, selectedColor, false);
                }
            }
        }, 0);
    },
    _updateMediaJustifyButton: function (commandState) {
        if (!this.lastMediaClicked) {
            return;
        }
        const $paragraphDropdownButton = this.toolbar.$el.find('#paragraphDropdownButton, #mediaParagraphDropdownButton');
        // Change the ID to prevent OdooEditor from controlling it as this is
        // custom behavior for media.
        $paragraphDropdownButton.attr('id', 'mediaParagraphDropdownButton');
        let resetAlignment = true;
        if (!commandState) {
            const justifyMapping = [
                ['float-start', 'justifyLeft'],
                ['mx-auto', 'justifyCenter'],
                ['float-end', 'justifyRight'],
            ];
            commandState = (justifyMapping.find(pair => (
                this.lastMediaClicked.classList.contains(pair[0]))
            ) || [])[1];
            resetAlignment = !commandState;
        }
        const $buttons = this.toolbar.$el.find('#justify div.btn');
        let newClass;
        if (commandState) {
            const direction = commandState.replace('justify', '').toLowerCase();
            newClass = `fa-align-${direction === 'full' ? 'justify' : direction}`;
            resetAlignment = !['float-start', 'mx-auto', 'float-end'].some(className => (
                this.lastMediaClicked.classList.contains(className)
            ));
        }
        for (const button of $buttons) {
            button.classList.toggle('active', !resetAlignment && button.id === commandState);
        }
        $paragraphDropdownButton.removeClass((index, className) => (
            (className.match(/(^|\s)fa-align-\w+/g) || []).join(' ')
        ));
        if (commandState && !resetAlignment) {
            $paragraphDropdownButton.addClass(newClass);
        } else {
            // Ensure we always display an icon in the align toolbar button.
            $paragraphDropdownButton.addClass('fa-align-justify');
        }
    },
    _updateFaResizeButtons: function () {
        if (!this.lastMediaClicked) {
            return;
        }
        const $buttons = this.toolbar.$el.find('#fa-resize div');
        const match = this.lastMediaClicked.className.match(/\s*fa-([0-9]+)x/);
        const value = match && match[1] ? match[1] : '1';
        for (const button of $buttons) {
            button.classList.toggle('active', button.dataset.value === value);
        }
    },
    _getEditorOptions: function (options) {
        const finalOptions = {...this.defaultOptions, ...options};
        // autohideToolbar is true by default (false by default if navbar present).
        finalOptions.autohideToolbar = typeof finalOptions.autohideToolbar === 'boolean'
            ? finalOptions.autohideToolbar
            : !finalOptions.snippets;

        return finalOptions;
    },
    _insertSnippetMenu: function () {
        return this.snippetsMenu.insertBefore(this.$el);
    },
    /**
     * If the element holds a translation, saves it. Otherwise, fallback to the
     * standard saving but with the lang kept.
     *
     * @override
     */
    _saveTranslationElement: function ($el, context, withLang = true) {
        if ($el.data('oe-translation-initial-sha')) {
            const $els = $el;
            const translations = {};
            translations[context.lang] = Object.assign({}, ...$els.toArray().map(
                (x) => ({
                    [$(x).data('oe-translation-initial-sha')]: this._getEscapedElement($(x)).html()
                })
            ));
            return this._rpc({
                model: $els.data('oe-model'),
                method: 'update_field_translations_sha',
                args: [
                    [+$els.data('oe-id')],
                    $els.data('oe-field'),
                    translations,
                ],
                context: context,
            });
        } else {
            var viewID = $el.data('oe-id');
            if (!viewID) {
                return Promise.resolve();
            }

            return this._rpc({
                model: 'ir.ui.view',
                method: 'save',
                args: [
                    viewID,
                    this._getEscapedElement($el).prop('outerHTML'),
                    !$el.data('oe-expression') && $el.data('oe-xpath') || null, // Note: hacky way to get the oe-xpath only if not a t-field
                ],
                context: context,
            }, withLang ? undefined : {
                noContextKeys: 'lang',
            });
        }
    },
    _getPowerboxOptions: function () {
        const editorOptions = this.options;
        const categories = [];
        const commands = [
            {
                category: _t('Structure'),
                name: _t('Quote'),
                priority: 30,
                description: _t('Add a blockquote section.'),
                fontawesome: 'fa-quote-right',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    this.odooEditor.execCommand('setTag', 'blockquote');
                },
            },
            {
                category: _t('Structure'),
                name: _t('Code'),
                priority: 20,
                description: _t('Add a code section.'),
                fontawesome: 'fa-code',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    this.odooEditor.execCommand('setTag', 'pre');
                },
            },
            {
                category: _t('Basic blocks'),
                name: _t('Signature'),
                description: _t('Insert your signature.'),
                fontawesome: 'fa-pencil-square-o',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: async () => {
                    const res = await this._rpc({
                        model: 'res.users',
                        method: 'read',
                        args: [this.getSession().uid, ['signature']],
                    });
                    if (res && res[0] && res[0].signature) {
                        this.odooEditor.execCommand('insert', parseHTML(res[0].signature));
                    }
                },
            },
        ];
        if (!editorOptions.inlineStyle) {
            commands.push(
                {
                    category: _t('Structure'),
                    name: _t('2 columns'),
                    priority: 13,
                    description: _t('Convert into 2 columns.'),
                    fontawesome: 'fa-columns',
                    callback: () => this.odooEditor.execCommand('columnize', 2, editorOptions.insertParagraphAfterColumns),
                    isDisabled: () => {
                        if (!this.odooEditor.isSelectionInBlockRoot()) {
                            return true;
                        }
                        const anchor = this.odooEditor.document.getSelection().anchorNode;
                        const row = closestElement(anchor, '.o_text_columns .row');
                        return row && row.childElementCount === 2;
                    },
                },
                {
                    category: _t('Structure'),
                    name: _t('3 columns'),
                    priority: 12,
                    description: _t('Convert into 3 columns.'),
                    fontawesome: 'fa-columns',
                    callback: () => this.odooEditor.execCommand('columnize', 3, editorOptions.insertParagraphAfterColumns),
                    isDisabled: () => {
                        if (!this.odooEditor.isSelectionInBlockRoot()) {
                            return true;
                        }
                        const anchor = this.odooEditor.document.getSelection().anchorNode;
                        const row = closestElement(anchor, '.o_text_columns .row');
                        return row && row.childElementCount === 3;
                    },
                },
                {
                    category: _t('Structure'),
                    name: _t('4 columns'),
                    priority: 11,
                    description: _t('Convert into 4 columns.'),
                    fontawesome: 'fa-columns',
                    callback: () => this.odooEditor.execCommand('columnize', 4, editorOptions.insertParagraphAfterColumns),
                    isDisabled: () => {
                        if (!this.odooEditor.isSelectionInBlockRoot()) {
                            return true;
                        }
                        const anchor = this.odooEditor.document.getSelection().anchorNode;
                        const row = closestElement(anchor, '.o_text_columns .row');
                        return row && row.childElementCount === 4;
                    },
                },
                {
                    category: _t('Structure'),
                    name: _t('Remove columns'),
                    priority: 10,
                    description: _t('Back to one column.'),
                    fontawesome: 'fa-columns',
                    callback: () => this.odooEditor.execCommand('columnize', 0),
                    isDisabled: () => {
                        if (!this.odooEditor.isSelectionInBlockRoot()) {
                            return true;
                        }
                        const anchor = this.odooEditor.document.getSelection().anchorNode;
                        const row = closestElement(anchor, '.o_text_columns .row');
                        return !row;
                    },
                },
            );
        }
        if (editorOptions.allowCommandLink) {
            categories.push({ name: _t('Navigation'), priority: 40 });
            commands.push(
                {
                    category: _t('Navigation'),
                    name: _t('Link'),
                    priority: 40,
                    description: _t('Add a link.'),
                    fontawesome: 'fa-link',
                    callback: () => {
                        this.toggleLinkTools({forceDialog: true});
                    },
                },
                {
                    category: _t('Navigation'),
                    name: _t('Button'),
                    priority: 30,
                    description: _t('Add a button.'),
                    fontawesome: 'fa-link',
                    callback: () => {
                        this.toggleLinkTools({forceDialog: true});
                        // Force the button style after the link modal is open.
                        setTimeout(() => {
                            $(".o_link_dialog .link-style[value=primary]").click();
                        }, 150);
                    },
                },
            );
        }
        if (editorOptions.allowCommandImage || editorOptions.allowCommandVideo) {
            categories.push({ name: _t('Media'), priority: 50 });
        }
        if (editorOptions.allowCommandImage) {
            commands.push({
                category: _t('Media'),
                name: _t('Image'),
                priority: 40,
                description: _t('Insert an image.'),
                fontawesome: 'fa-file-image-o',
                callback: () => {
                    this.openMediaDialog();
                },
            });
        }
        if (editorOptions.allowCommandVideo) {
            commands.push({
                category: _t('Media'),
                name: _t('Video'),
                priority: 30,
                description: _t('Insert a video.'),
                fontawesome: 'fa-file-video-o',
                callback: () => {
                    this.openMediaDialog({noVideos: false, noImages: true, noIcons: true, noDocuments: true});
                },
            });
        }
        if (editorOptions.powerboxCategories) {
            categories.push(...editorOptions.powerboxCategories);
        }
        if (editorOptions.powerboxCommands) {
            commands.push(...editorOptions.powerboxCommands);
        }
        return {commands, categories};
    },

    /**
     * Returns the editable areas on the page.
     *
     * @returns {jQuery}
     */
    editable: function () {
        return $('#wrapwrap [data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                return !$(this).closest('.o_not_editable').length;
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .add('.o_editable');
    },

    /**
     * Searches all the dirty element on the page and saves them one by one. If
     * one cannot be saved, this notifies it to the user and restarts rte
     * edition.
     *
     * @param {Object} [context] - the context to use for saving rpc, default to
     *                           the editor context found on the page
     * @return {Promise} rejected if the save cannot be done
     */
    _saveViewBlocks: function (context) {
        // TODO should be review to probably not search in the whole body,
        // iframe or not.
        const $ = (this.$editable[0].ownerDocument.defaultView.$ || window.$);
        const $allBlocks = $((this.options || {}).savableSelector).filter('.o_dirty');

        const $dirty = $('.o_dirty');
        $dirty
            .removeAttr('contentEditable')
            .removeClass('o_dirty oe_carlos_danger o_is_inline_editable');

        $('.o_editable')
            .removeClass('o_editable o_is_inline_editable o_editable_date_field_linked o_editable_date_field_format_changed');

        const saveElementFuncName = this.options.enableTranslation
            ? '_saveTranslationElement'
            : '_saveElement';

        // Group elements to save if possible.
        const groupedElements = _.groupBy($allBlocks.toArray(), el => {
            const model = el.dataset.oeModel;
            const field = el.dataset.oeField;

            // There are elements which have no linked model as something
            // special is to be done "to save them" (potential override to
            // `_saveElement` which is expected to be called for each unique
            // dirty element). In that case, do not group those elements.
            if (!model) {
                return _.uniqueId('special-element-to-save-');
            }

            // Do not group elements which are parts of views, unless we are
            // in translate mode.
            if (!this.options.enableTranslation
                    && (model === 'ir.ui.view' && field === 'arch')) {
                return _.uniqueId('view-part-to-save-');
            }

            // Otherwise, group elements which are from the same field of the
            // same record (`_saveElement` will only consider the first one and
            // `_saveTranslationElement` can handle the set if it makes sense).
            return `${model}::${el.dataset.oeId}::${field}`;
        });
        const proms = Object.values(groupedElements).map(els => {
            const $els = $(els);

            $els.find('[class]').filter(function () {
                if (!this.getAttribute('class').match(/\S/)) {
                    this.removeAttribute('class');
                }
            });

            // TODO: Add a queue with concurrency limit in webclient
            return this.saving_mutex.exec(() => {
                return this[saveElementFuncName]($els, context || this.options.context)
                .then(function () {
                    $els.removeClass('o_dirty');
                }).guardedCatch(function (response) {
                    // because ckeditor regenerates all the dom, we can't just
                    // setup the popover here as everything will be destroyed by
                    // the DOM regeneration. Add markings instead, and returns a
                    // new rejection with all relevant info
                    var id = _.uniqueId('carlos_danger_');
                    $els.addClass('o_dirty o_editable oe_carlos_danger ' + id);
                    $('.o_editable.' + id)
                        .removeClass(id)
                        .popover({
                            trigger: 'hover',
                            content: response.message.data.message || '',
                            placement: 'auto',
                        })
                        .popover('show');
                });
            });
        });
        return Promise.all(proms).then(function () {
            window.onbeforeunload = null;
        }).guardedCatch((failed) => {
            // If there were errors, re-enable edition
            this.cancel(false);
        });
    },
    // TODO unused => remove or reuse as it should be
    _attachTooltips: function () {
        $(document.body)
            .tooltip({
                selector: '[data-oe-readonly]',
                container: 'body',
                trigger: 'hover',
                delay: {'show': 1000, 'hide': 100},
                placement: 'bottom',
                title: _t("Readonly field")
            })
            .on('click', function () {
                $(this).tooltip('hide');
            });
    },
    /**
     * Gets jQuery cloned element with internal text nodes escaped for XML
     * storage.
     *
     * @private
     * @param {jQuery} $el
     * @return {jQuery}
     */
    _getEscapedElement: function ($el) {
        var escaped_el = $el.clone();
        var to_escape = escaped_el.find('*').addBack();
        to_escape = to_escape.not(to_escape.filter('object,iframe,script,style,[data-oe-model][data-oe-model!="ir.ui.view"]').find('*').addBack());
        to_escape.contents().each(function () {
            if (this.nodeType === 3) {
                this.nodeValue = $('<div />').text(this.nodeValue).html();
            }
        });
        return escaped_el;
    },
    /**
     * Saves one (dirty) element of the page.
     *
     * @private
     * @param {jQuery} $el - the element to save
     * @param {Object} context - the context to use for the saving rpc
     * @param {boolean} [withLang=false]
     *        false if the lang must be omitted in the context (saving "master"
     *        page element)
     */
    _saveElement: function ($el, context, withLang) {
        var viewID = $el.data('oe-id');
        if (!viewID) {
            return Promise.resolve();
        }

        // remove ZeroWidthSpace from odoo field value
        // ZeroWidthSpace may be present from OdooEditor edition process
        let escapedHtml = this._getEscapedElement($el).prop('outerHTML');

        return this._rpc({
            model: 'ir.ui.view',
            method: 'save',
            args: [
                viewID,
                escapedHtml,
                !$el.data('oe-expression') && $el.data('oe-xpath') || null, // Note: hacky way to get the oe-xpath only if not a t-field
            ],
            context: context,
        }, withLang ? undefined : {
            noContextKeys: 'lang',
        });
    },

    /**
     * Reloads the page in non-editable mode, with the right scrolling.
     *
     * @private
     * @returns {Promise} (never resolved, the page is reloading anyway)
     */
    _reload: function () {
        window.location.hash = 'scrollTop=' + window.document.body.scrollTop;
        if (window.location.search.indexOf('enable_editor') >= 0) {
            window.location.href = window.location.href.replace(/&?enable_editor(=[^&]*)?/g, '');
        } else {
            window.location.reload(true);
        }
        return new Promise(function () {});
    },
    _onAttachmentChange(attachment) {
        // todo: to remove when removing the legacy field_html
        this.trigger_up('attachment_changed', attachment);
        if (this.options.onAttachmentChange) {
            this.options.onAttachmentChange(attachment);
        }
    },
    _onSelectionChange() {
        if (this.odooEditor.autohideToolbar && this.linkPopover) {
            const selectionInLink = getInSelection(this.odooEditor.document, 'a') === this.linkPopover.target;
            const isVisible = this.linkPopover.el.offsetParent;
            if (isVisible && !selectionInLink) {
                this.linkPopover.hide();
            }
        }
    },
    _onDocumentMousedown: function (e) {
        if (!e.target.classList.contains('o_editable_date_field_linked')) {
            this.$editable.find('.o_editable_date_field_linked').removeClass('o_editable_date_field_linked');
        }
        const closestDialog = e.target.closest('.o_dialog, .o_web_editor_dialog');
        if (
            e.target.closest('.oe-toolbar,.oe-powerbox-wrapper,.o_we_crop_widget') ||
            (closestDialog && closestDialog.querySelector('.o_select_media_dialog, .o_link_dialog'))) {
            this._shouldDelayBlur = true;
        } else {
            if (this._pendingBlur && !e.target.closest('.o_wysiwyg_wrapper')) {
                // todo: to remove when removing the legacy field_html
                this.trigger_up('wysiwyg_blur');
                this.options.onWysiwygBlur && this.options.onWysiwygBlur();
                this._pendingBlur = false;
            }
            this._shouldDelayBlur = false;
        }
    },
    _onBlur: function () {
        if (this._shouldDelayBlur) {
            this._pendingBlur = true;
        } else {
            // todo: to remove when removing the legacy field_html
            this.trigger_up('wysiwyg_blur');
            this.options.onWysiwygBlur && this.options.onWysiwygBlur();
        }
    },
    _onScroll: function(ev) {
        if (ev.target.contains(this.$editable[0])) {
            this.scrollContainer = ev.target;
            this.odooEditor.updateToolbarPosition();
        }
    },
    _signalOffline: function () {
        this._isOnline = false;
    },
    _signalOnline: async function () {
        clearTimeout(this._offlineTimeout);
        this._offlineTimeout = undefined;

        if (this._isOnline || !navigator.onLine) {
            return;
        }
        this._isOnline = true;
        if (!this.ptp) return;

        // If it was disconnected to some peers, send the join signal again.
        this.ptp.notifyAllClients('ptp_join');
        // Send last step to all peers. If the peers cannot add the step, they
        // will ask for missing steps.
        this.ptp.notifyAllClients('oe_history_step', peek(this.odooEditor.historyGetSteps()), { transport: 'rtc' });
    },
    /**
     * Process missing steps received from a peer.
     *
     * @private
     * @param {Array<Object>|-1} missingSteps
     * @return {Promise<boolean>} true if missing steps have been processed
     */
    async _processMissingSteps(missingSteps) {
        // If missing steps === -1, it means that either:
        // - the step.clientId has a stale document
        // - the step.clientId has a snapshot and does not includes the step in
        //   its history
        // - if another share history id
        //   - because the step.clientId has reset from the server and
        //     step.clientId is not synced with this client
        //   - because the step.clientId is in a network partition
        if (missingSteps === -1 || !missingSteps.length) {
            return false;
        }
        this.ptp && this.odooEditor.onExternalHistorySteps(missingSteps);
        return true;
    },
    _showConflictDialog() {
        if (this._conflictDialogOpened) return;
        const $dialogContent = $(QWeb.render('web_editor.collaboration-conflict-dialog'));
        $dialogContent.append($(this.odooEditor.editable).clone());
        const dialog = new Dialog(this, {
            title: _t("Content conflict"),
            $content: $dialogContent,
            size: 'medium',
        });
        this._conflictDialogOpened = true;
        dialog.open({shouldFocusButtons: true});
        dialog.on('closed', undefined, () => {
            this._conflictDialogOpened = false;
        });
    },
    _getLastHistoryStepId: function (value) {
        const matchId = value.match(/data-last-history-steps="(?:[0-9]+,)*([0-9]+)"/);
        return matchId && matchId[1];
    },
    _generateClientId: function () {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2, 52)).toString();
    },
    _getNewPtp() {
        const rpcMutex = new Mutex();
        const {collaborationChannel} = this.options;
        const modelName = collaborationChannel.collaborationModelName;
        const fieldName = collaborationChannel.collaborationFieldName;
        const resId = collaborationChannel.collaborationResId;

        // Wether or not the history has been sent or received at least
        // once.
        this._historySyncAtLeastOnce = false;

        return new PeerToPeer({
            peerConnectionConfig: { iceServers: this._iceServers },
            currentClientId: this._currentClientId,
            broadcastAll: (rpcData) => {
                return rpcMutex.exec(async () => {
                    return this._rpc({
                        route: '/web_editor/bus_broadcast',
                        params: {
                            model_name: modelName,
                            field_name: fieldName,
                            res_id: resId,
                            bus_data: rpcData,
                        },
                    });
                });
            },
            onRequest: {
                get_start_time: () => this._startCollaborationTime,
                get_client_name: async () => {
                    if (!this._userName) {
                        this._userName = (await this._rpc({
                            model: "res.users",
                            method: "search_read",
                            args: [
                                [['id', '=', this.getSession().uid]],
                                ['name']
                            ],
                        }))[0].name;
                    }
                    return this._userName;
                },
                get_client_avatar: () => `${browser.location.origin}/web/image?model=res.users&field=avatar_128&id=${encodeURIComponent(this.getSession().uid)}`,
                get_missing_steps: (params) => this.odooEditor.historyGetMissingSteps(params.requestPayload),
                get_history_from_snapshot: () => this._getHistorySnapshot(),
                get_collaborative_selection: () => this.odooEditor.getCurrentCollaborativeSelection(),
                recover_document: (params) => {
                    const { serverDocumentId, fromStepId } = params.requestPayload;
                    if (!this.odooEditor.historyGetBranchIds().includes(serverDocumentId)) {
                        return;
                    }
                    return {
                        missingSteps: this.odooEditor.historyGetMissingSteps({ fromStepId }),
                        snapshot: this._getHistorySnapshot(),
                    };
                },
            },
            onNotification: async ({ fromClientId, notificationName, notificationPayload }) => {
                switch (notificationName) {
                    case 'ptp_remove':
                        this.odooEditor.multiselectionRemove(notificationPayload);
                        break;
                    case 'ptp_disconnect':
                        this.ptp.removeClient(fromClientId);
                        this.odooEditor.multiselectionRemove(fromClientId);
                        break;
                    case 'rtc_data_channel_open': {
                        fromClientId = notificationPayload.connectionClientId;
                        const remoteStartTime = await this.requestClient(fromClientId, 'get_start_time', undefined, { transport: 'rtc' });
                        if (remoteStartTime === REQUEST_ERROR) return;
                        this.ptp.clientsInfos[fromClientId].startTime = remoteStartTime;

                        if (!this._historySyncAtLeastOnce) {
                            const localClient = { id: this._currentClientId, startTime: this._startCollaborationTime };
                            const remoteClient = { id: fromClientId, startTime: remoteStartTime };
                            if (isClientFirst(localClient, remoteClient)) {
                                this._historySyncAtLeastOnce = true;
                                this._historySyncFinished = true;
                            } else {
                                this._resetCollabRequests();
                                const response = await this._resetFromClient(fromClientId, this._lastCollaborationResetId);
                                if (response === REQUEST_ERROR) {
                                    return;
                                }
                            }
                        } else {
                            // Make both send their last step to each other to
                            // ensure they are in sync.
                            this.ptp.notifyAllClients('oe_history_step', peek(this.odooEditor.historyGetSteps()), { transport: 'rtc' });
                            this._setCollaborativeSelection(fromClientId);
                        }

                        const getClientNamePromise = this.requestClient(
                            fromClientId, 'get_client_name', undefined, { transport: 'rtc' }
                        ).then((clientName) => {
                            if (clientName === REQUEST_ERROR) return;
                            this.ptp.clientsInfos[fromClientId].clientName = clientName;
                            this.odooEditor.multiselectionRefresh();
                        });
                        const getClientAvatar = this.requestClient(
                            fromClientId, 'get_client_avatar', undefined, { transport: 'rtc' }
                        ).then(clientAvatarUrl => {
                            if (clientAvatarUrl === REQUEST_ERROR) return;
                            this.ptp.clientsInfos[fromClientId].clientAvatarUrl = clientAvatarUrl;
                            this.odooEditor.multiselectionRefresh();
                        });
                        await Promise.all([getClientAvatar, getClientNamePromise]);
                        break;
                    }
                    case 'oe_history_step':
                        if (this._historySyncFinished) {
                            this.odooEditor.onExternalHistorySteps([notificationPayload]);
                        } else {
                            this._historyStepsBuffer.push(notificationPayload);
                        }
                        break;
                    case 'oe_history_set_selection': {
                        const client = this.ptp.clientsInfos[fromClientId];
                        if (!client) {
                            return;
                        }
                        const selection = notificationPayload;
                        selection.clientName = client.clientName;
                        selection.clientAvatarUrl = client.clientAvatarUrl;
                        this.odooEditor.onExternalMultiselectionUpdate(selection);
                        break;
                    }
                }
            }
        });
    },
    _getCollaborationClientAvatarUrl() {
        return `${browser.location.origin}/web/image?model=res.users&field=avatar_128&id=${encodeURIComponent(this.getSession().uid)}`
    },
    _stopPeerToPeer: function () {
        this._joiningPtp = false;
        this._ptpJoined = false;
        this._resetCollabRequests();
        this.ptp && this.ptp.stop();
    },
    _joinPeerToPeer: function () {
        this.$editable[0].removeEventListener('focus', this._joinPeerToPeer);
        if (this._peerToPeerLoading) {
            return this._peerToPeerLoading.then(async () => {
                this._joiningPtp = true;
                if (this._isDocumentStale) {
                    const success = await this._resetFromServerAndResyncWithClients();
                    if (!success) return;
                }
                this.ptp.notifyAllClients('ptp_join');
                this._joiningPtp = false;
                this._ptpJoined = true;
            });
        }
    },
    async _setCollaborativeSelection(fromClientId) {
        const remoteSelection = await this.requestClient(fromClientId, 'get_collaborative_selection', undefined, { transport: 'rtc' });
        if (remoteSelection === REQUEST_ERROR) return;
        if (remoteSelection) {
            this.odooEditor.onExternalMultiselectionUpdate(remoteSelection);
        }
    },
    /**
     * Get peer to peer clients.
     */
    _getPtpClients() {
        const clients = Object.entries(this.ptp.clientsInfos).map(([clientId, clientInfo]) => ({id: clientId, ...clientInfo}));
        return clients.sort((a, b) => isClientFirst(a, b) ? -1 : 1);
    },
    async _getCurrentRecord() {
        const records = await this._rpc({
            model: this.options.collaborationChannel.collaborationModelName,
            method: "read",
            args: [
                [this.options.collaborationChannel.collaborationResId],
                [this.options.collaborationChannel.collaborationFieldName]
            ],
        });
        return records[0];
    },
    _isLastDocumentStale() {
        if (!this._serverLastStepId) {
            return false;
        }
        return !this.odooEditor.historyGetBranchIds().includes(this._serverLastStepId);
    },
    /**
     * Update the server document last step id and recover from a stale document
     * if this client does not have that step in its history.
     */
    _onServerLastIdUpdate(last_step_id) {
        this._serverLastStepId = last_step_id;
        // Check if the current document is stale.
        this._isDocumentStale = this._isLastDocumentStale();
        if (this._isDocumentStale && this._ptpJoined) {
            return this._recoverFromStaleDocument();
        } else if (this._isDocumentStale && this._joiningPtp) {
            // In case there is a stale document while a previous recovery is
            // ongoing.
            this._resetCollabRequests();
            this._joinPeerToPeer();
        }
    },
    /**
     * Try to recover from a stale document.
     *
     * The strategy is:
     *
     * 1.  Try to get a converging document from the other peers.
     *
     * 1.1 By recovery from missing steps: it is the best possible case of
     *     retrieval.
     *
     * 1.2 By recovery from snapshot: it reset the whole editor (destroying
     *     changes and selection made by the user).
     *
     * 2. Reset from the server:
     *    If the recovery from the other peers fails, reset from the server.
     *
     *    As we know we have a stale document, we need to reset it at least from
     *    the server. We shouldn't wait too long for peers to respond because
     *    the longer we wait for an unresponding peer, the longer a user can
     *    edit a stale document.
     *
     *    The peers timeout is set to PTP_MAX_RECOVERY_TIME.
     */
    async _recoverFromStaleDocument() {
        return new Promise((resolve) => {
            // 1. Try to recover a converging document from other peers.
            const resetCollabCount = this._lastCollaborationResetId;

            const allPeers = this._getPtpClients().map(client => client.id);

            if (allPeers.length === 0) {
                if (this._isDocumentStale) {
                    this._showConflictDialog();
                    resolve();
                    return this._resetFromServerAndResyncWithClients();
                }
            }

            let hasRetrievalBudgetTimeout = false;
            let snapshots = [];
            let nbPendingResponses = allPeers.length;

            const success = () => {
                resolve();
                clearTimeout(timeout);
            };

            for (const peerId of allPeers) {
                this.requestClient(
                    peerId,
                    'recover_document', {
                        serverDocumentId: this._serverLastStepId,
                        fromStepId: peek(this.odooEditor.historyGetBranchIds()),
                    },
                    { transport: 'rtc' }
                ).then((response) => {
                    nbPendingResponses--;
                    if (
                        response === REQUEST_ERROR ||
                        resetCollabCount !== this._lastCollaborationResetId ||
                        hasRetrievalBudgetTimeout ||
                        !response ||
                        !this._isDocumentStale
                    ) {
                        if (nbPendingResponses <= 0) {
                            processSnapshots();
                        }
                        return;
                    }
                    this._processMissingSteps(response.missingSteps);
                    this._isDocumentStale = this._isLastDocumentStale();
                    snapshots.push(response.snapshot);
                    if (nbPendingResponses < 1) {
                        processSnapshots();
                    }
                });
            }

            // Only process the snapshots after having received a response from all
            // the peers or after PTP_MAX_RECOVERY_TIME in order to try to recover
            // from missing steps.
            const processSnapshots = async () => {
                this._isDocumentStale = this._isLastDocumentStale();
                if (!this._isDocumentStale) {
                    return success();
                }
                if (snapshots[0]) {
                    this._showConflictDialog();
                }
                for (const snapshot of snapshots) {
                    this._applySnapshot(snapshot);
                    this._isDocumentStale = this._isLastDocumentStale();
                    // Prevent reseting from another snapshot if the document
                    // converge.
                    if (!this._isDocumentStale) {
                        return success();
                    }
                }

                // 2. If the document is still stale, try to recover from the server.
                if (this._isDocumentStale) {
                    this._showConflictDialog();
                    await this._resetFromServerAndResyncWithClients();
                }

                success();
            }

            // Wait PTP_MAX_RECOVERY_TIME to retrieve data from other peers to
            // avoid reseting from the server if possible.
            const timeout = setTimeout(() => {
                if (resetCollabCount !== this._lastCollaborationResetId) return;
                hasRetrievalBudgetTimeout = true;
                this._onRecoveryClientTimeout(processSnapshots);
            }, PTP_MAX_RECOVERY_TIME);
        });
    },
    /**
     * Callback for when the timeout PTP_MAX_RECOVERY_TIME fires.
     *
     * Used to be hooked in tests.
     *
     * @param {Function} processSnapshots The snapshot processing function.
     */
    async _onRecoveryClientTimeout(processSnapshots) {
        processSnapshots();
    },
    /**
     * Reset the document from the server and resync with the clients.
     */
    async _resetFromServerAndResyncWithClients() {
        let collaborationResetId = this._lastCollaborationResetId;
        const record = await this._getCurrentRecord();
        if (collaborationResetId !== this._lastCollaborationResetId) return;

        const content = record[this.options.collaborationChannel.collaborationFieldName];
        const lastHistoryId = content && this._getLastHistoryStepId(content);
        // If a change was made in the document while retrieving it, the
        // lastHistoryId will be different if the odoo bus did not have time to
        // notify the user.
        if (this._serverLastStepId !== lastHistoryId) {
            // todo: instrument it to ensure it never happens
            throw new Error('Concurency detected while recovering from a stale document. The last history id of the server is different from the history id received by the html_field_write event.');
        }

        this._isDocumentStale = false;
        this.resetValue(content);

        // After resetting from the server, try to resynchronise with a peer as
        // if it was the first time connecting to a peer in order to retrieve a
        // proper snapshot (e.g. This case could arise if we tried to recover
        // from a client but the timeout (PTP_MAX_RECOVERY_TIME) was reached
        // before receiving a response).
        this._historySyncAtLeastOnce = false;
        this._resetCollabRequests();
        collaborationResetId = this._lastCollaborationResetId;
        this._startCollaborationTime = new Date().getTime();
        await Promise.all(this._getPtpClients().map((client) => {
            // Reset from the fastest client. The first client to reset will set
            // this._historySyncAtLeastOnce to true canceling the other peers
            // resets.
            return this._resetFromClient(client.id, collaborationResetId);
        }));
        return true;
    },
    _resetCollabRequests() {
        this._lastCollaborationResetId++;
        // By aborting the current requests from ptp, we ensure that the ongoing
        // `Wysiwyg.requestClient` will return REQUEST_ERROR. Most requests that
        // calls `Wysiwyg.requestClient` might want to check if the response is
        // REQUEST_ERROR.
        this.ptp && this.ptp.abortCurrentRequests();
    },
    async _resetFromClient(fromClientId, resetCollabCount) {
        this._historySyncFinished = false;
        this._historyStepsBuffer = [];
        const snapshot = await this.requestClient(fromClientId, 'get_history_from_snapshot', undefined, { transport: 'rtc' });
        if (snapshot === REQUEST_ERROR) {
            return REQUEST_ERROR;
        }
        if (resetCollabCount !== this._lastCollaborationResetId) {
            return;
        }
        // Ensure that the history hasn't been synced by another client before
        // this `get_history_from_snapshot` finished.
        if (this._historySyncAtLeastOnce) {
            return;
        }
        const applied = this._applySnapshot(snapshot);
        if (!applied) {
            return;
        }
        this._historySyncFinished = true;
        // In case there are steps received in the meantime, process them.
        if (this._historyStepsBuffer.length) {
            this.odooEditor.onExternalHistorySteps(this._historyStepsBuffer);
            this._historyStepsBuffer = [];
        }
        this._setCollaborativeSelection(fromClientId);
    },
    async requestClient(clientId, requestName, requestPayload, params) {
        return this.ptp.requestClient(clientId, requestName, requestPayload, params).catch((e) => {
            if (e instanceof RequestError) {
                return REQUEST_ERROR;
            } else {
                throw e;
            }
        });
    },
    /**
     * Reset the value and history of the editor.
     */
    async resetValue(value) {
        this.setValue(value);
        this.odooEditor.historyReset();
        this._historyShareId = Math.floor(Math.random() * Math.pow(2,52)).toString();
        this._serverLastStepId = value && this._getLastHistoryStepId(value);
        if (this._serverLastStepId) {
            this.odooEditor.historySetInitialId(this._serverLastStepId);
        }
    },
    /**
     * Reset the editor with a new value and potientially new options.
     */
    resetEditor: async function (value, options) {
        await this._peerToPeerLoading;
        this.$editable[0].removeEventListener('focus', this._joinPeerToPeer);
        if (options) {
            this.options = this._getEditorOptions(options);
        }
        const {collaborationChannel} = this.options;
        this._stopPeerToPeer();
        this._collaborationStopBus && this._collaborationStopBus();
        this._isDocumentStale = false;
        this._rulesCache = undefined; // Reset the cache of rules.
        // If there is no collaborationResId, the record has been deleted.
        if (!collaborationChannel || !collaborationChannel.collaborationResId) {
            this._currentClientId = undefined;
            this.resetValue(value);
            return;
        }
        this._currentClientId = this._generateClientId();
        this.odooEditor.collaborationSetClientId(this._currentClientId);
        this.resetValue(value);
        this.setupCollaboration(collaborationChannel);
        // Wait until editor is focused to join the peer to peer network.
        this.$editable[0].addEventListener('focus', this._joinPeerToPeer);

        await this._peerToPeerLoading;
    },
    _getHistorySnapshot() {
        return Object.assign(
            {},
            this.odooEditor.historyGetSnapshotSteps(),
            { historyShareId: this._historyShareId }
        );
    },
    _applySnapshot(snapshot) {
        const { steps, historyIds, historyShareId } = snapshot;
        // If there is no serverLastStepId, it means that we use a document
        // that is not versionned yet.
        const isStaleDocument = this._serverLastStepId && !historyIds.includes(this._serverLastStepId);
        if (isStaleDocument) {
            return;
        }
        this._historyShareId = historyShareId;
        this._historySyncAtLeastOnce = true;
        this.odooEditor.historyResetFromSteps(steps, historyIds);
        this.odooEditor.historyResetLatestComputedSelection();
        return true;
    },
    /**
     * Set contenteditable=false for all `.o_not_editable` found within node if
     * node is an element.
     *
     * For all `.o_not_editable` element found, the attribute contenteditable
     * will be removed if the class is removed.
     *
     * @param {Node} node
     */
    _setONotEditable: function (node) {
        const nodes = (node && node.querySelectorAll && node.querySelectorAll('.o_not_editable:not([contenteditable=false])')) || [];
        for (const node of nodes) {
            node.setAttribute('contenteditable', false);
            let observer = this._oNotEditableObservers.get(node);
            if (!observer) {
                observer = new MutationObserver((records) => {
                    for (const record of records) {
                        if (record.type === 'attributes' && record.attributeName === 'class') {
                            // Remove contenteditable=false on nodes that were
                            // previsouly o_not_editable but are no longer
                            // o_not_editable.
                            if (!node.classList.contains('o_not_editable')) {
                                this.odooEditor.observerUnactive('_setONotEditable');
                                node.removeAttribute('contenteditable');
                                this.odooEditor.observerActive('_setONotEditable');
                                observer.disconnect();
                                this._oNotEditableObservers.delete(node);
                            }
                        }
                    }
                });
                this._oNotEditableObservers.set(node, observer);
                observer.observe(node, {
                    attributes: true,
                });
            }
        }
    },
    _attachHistoryIds(editable = this.odooEditor.editable) {
        if (this.options.collaborative) {
            const historyIds = this.odooEditor.historyGetBranchIds().join(',');
            const firstChild = editable.children[0];
            if (firstChild) {
                firstChild.setAttribute('data-last-history-steps', historyIds);
            }
        }
    },
    _bindOnBlur() {
        this.$editable.on('blur', this._onBlur);
    },

});
Wysiwyg.activeCollaborationChannelNames = new Set();
Wysiwyg.activeWysiwygs = new Set();
//--------------------------------------------------------------------------
// Public helper
//--------------------------------------------------------------------------
/**
 * @param {Node} [ownerDocument] (document on which to get the selection)
 * @returns {Object}
 * @returns {Node} sc - start container
 * @returns {Number} so - start offset
 * @returns {Node} ec - end container
 * @returns {Number} eo - end offset
 */
Wysiwyg.getRange = function (ownerDocument) {
    const selection = (ownerDocument || document).getSelection();
    if (selection.rangeCount === 0) {
        return {
            sc: null,
            so: 0,
            ec: null,
            eo: 0,
        };
    }
    const range = selection.getRangeAt(0);

    return {
        sc: range.startContainer,
        so: range.startOffset,
        ec: range.endContainer,
        eo: range.endOffset,
    };
};
/**
 * @param {Node} startNode
 * @param {Number} startOffset
 * @param {Node} endNode
 * @param {Number} endOffset
 */
Wysiwyg.setRange = function (startNode, startOffset = 0, endNode = startNode, endOffset = startOffset) {
    const selection = document.getSelection();
    selection.removeAllRanges();

    const range = new Range();
    range.setStart(startNode, startOffset);
    range.setEnd(endNode, endOffset);
    selection.addRange(range);
};


// Check wether clientA is before clientB.
function isClientFirst(clientA, clientB) {
    if (clientA.startTime === clientB.startTime) {
        return clientA.id.localeCompare(clientB.id) === -1;
    } if (clientA.startTime === undefined || clientB.startTime === undefined) {
        return Boolean(clientA.startTime);
    } else {
        return clientA.startTime < clientB.startTime;
    }
};

return Wysiwyg;
});
odoo.define('web_editor.widget', function (require) {
'use strict';
    return {
        Dialog: require('wysiwyg.widgets.Dialog'),
        LinkDialog: require('wysiwyg.widgets.LinkDialog'),
    };
});
