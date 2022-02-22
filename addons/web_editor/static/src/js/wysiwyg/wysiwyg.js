odoo.define('web_editor.wysiwyg', function (require) {
'use strict';

const dom = require('web.dom');
const core = require('web.core');
const Widget = require('web.Widget');
const Dialog = require('web.Dialog');
const customColors = require('web_editor.custom_colors');
const {ColorPaletteWidget} = require('web_editor.ColorPalette');
const {ColorpickerWidget} = require('web.Colorpicker');
const concurrency = require('web.concurrency');
const { device } = require('web.config');
const weContext = require('web_editor.context');
const OdooEditorLib = require('@web_editor/../lib/odoo-editor/src/OdooEditor');
const snippetsEditor = require('web_editor.snippet.editor');
const Toolbar = require('web_editor.toolbar');
const weWidgets = require('wysiwyg.widgets');
const wysiwygUtils = require('@web_editor/js/common/wysiwyg_utils');
const weUtils = require('web_editor.utils');
const { PeerToPeer } = require('@web_editor/js/wysiwyg/PeerToPeer');
const { Mutex } = require('web.concurrency');

var _t = core._t;

const OdooEditor = OdooEditorLib.OdooEditor;
const getDeepRange = OdooEditorLib.getDeepRange;
const getInSelection = OdooEditorLib.getInSelection;
const isBlock = OdooEditorLib.isBlock;
const rgbToHex = OdooEditorLib.rgbToHex;
const preserveCursor = OdooEditorLib.preserveCursor;
const closestElement = OdooEditorLib.closestElement;

var id = 0;
const faZoomClassRegex = RegExp('fa-[0-9]x');
const mediaSelector = 'img, .fa, .o_image, .media_iframe_video';

const Wysiwyg = Widget.extend({
    xmlDependencies: [
    ],
    defaultOptions: {
        lang: 'odoo',
        colors: customColors,
        recordInfo: {context: {}},
        document: document,
    },
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.id = ++id;
        this.options = options;
        // autohideToolbar is true by default (false by default if navbar present).
        this.options.autohideToolbar = typeof this.options.autohideToolbar === 'boolean'
            ? this.options.autohideToolbar
            : !options.snippets;
        this.saving_mutex = new concurrency.Mutex();
        // Keeps track of color palettes per event name.
        this.colorpickers = {};
        this._onDocumentMousedown = this._onDocumentMousedown.bind(this);
        this._onBlur = this._onBlur.bind(this);
        this.customizableLinksSelector = 'a:not([data-toggle="tab"]):not([data-toggle="collapse"])';
    },
    /**
     *
     * @override
     */
    start: async function () {
        const _super = this._super;
        const self = this;

        var options = this._editorOptions();
        this._value = options.value;

        this.$editable = this.$editable || this.$el;
        this.$editable.html(this._value);
        this.$editable.data('wysiwyg', this);
        this.$editable.data('oe-model', options.recordInfo.res_model);
        this.$editable.data('oe-id', options.recordInfo.res_id);
        document.addEventListener('mousedown', this._onDocumentMousedown, true);
        this.$editable.on('blur', this._onBlur);

        this.toolbar = new Toolbar(this, this.options.toolbarTemplate);
        await this.toolbar.appendTo(document.createElement('void'));
        const commands = this._getCommands();

        let editorCollaborationOptions;
        if (
            options.collaborationChannel &&
            // Hack: check if mail module is installed.
            this.getSession()['notification_type']
        ) {
            editorCollaborationOptions = this.setupCollaboration(options.collaborationChannel);
        }

        const getYoutubeVideoElement = (url) => {
            const videoWidget = new weWidgets.VideoWidget(this, undefined, {});
            const src = videoWidget._createVideoNode(url).$video.attr('src');
            return videoWidget.getWrappedIframe(src)[0];
        };

        this.odooEditor = new OdooEditor(this.$editable[0], Object.assign({
            _t: _t,
            toolbar: this.toolbar.$el[0],
            document: this.options.document,
            autohideToolbar: !!this.options.autohideToolbar,
            isRootEditable: this.options.isRootEditable,
            placeholder: this.options.placeholder,
            controlHistoryFromDocument: this.options.controlHistoryFromDocument,
            getContentEditableAreas: this.options.getContentEditableAreas,
            defaultLinkAttributes: this.options.userGeneratedContent ? {rel: 'ugc' } : {},
            getYoutubeVideoElement: getYoutubeVideoElement,
            getContextFromParentRect: options.getContextFromParentRect,
            getPowerboxElement: () => {
                const selection = document.getSelection();
                if (selection.isCollapsed && selection.rangeCount) {
                    const node = closestElement(selection.anchorNode, 'P, DIV');
                    return !(node && node.hasAttribute && node.hasAttribute('data-oe-model')) && node;
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
                    return !(record.target.classList && record.target.classList.contains('o_header_standard'));
                });
            },
            commands: commands,
            plugins: options.editorPlugins,
        }, editorCollaborationOptions));

        const $wrapwrap = $('#wrapwrap');
        if ($wrapwrap.length) {
            $wrapwrap[0].addEventListener('scroll', this.odooEditor.multiselectionRefresh, { passive: true });
            this.$root = this.$root || $wrapwrap;
        }

        if (this._peerToPeerLoading) {
            // Now that the editor is loaded, wait for the peerToPeer to be
            // ready to join.
            this._peerToPeerLoading.then(() => this.ptp.notifyAllClients('ptp_join'));
        }

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
                        $field.find('img').attr('contenteditable', true);
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
            self.showTooltip = false;
            const $el = $(this);
            let params = {node: $el};
            $el.selectElement();

            if ($el.is('.fa')) {
                // save layouting classes from icons to not break the page if you edit an icon
                params.htmlClass = [...$el[0].classList].filter((className) => {
                    return !className.startsWith('fa') || faZoomClassRegex.test(className);
                }).join(' ');
            }

            self.openMediaDialog(params);
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

        $(this.odooEditor.editable).on('click', this._updateEditorUI.bind(this));
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
                    && !$target.attr('data-oe-model')
                    && !$target.find('> [data-oe-model]').length
                    && !$target[0].closest('.o_extra_menu_items')) {
                this.linkPopover = $target.data('popover-widget-initialized');
                if (!this.linkPopover) {
                    // TODO this code is ugly maybe the mutex should be in the
                    // editor root widget / the popover should not depend on
                    // editor panel (like originally intended but...) / ...
                    (async () => {
                        if (this.snippetsMenu) {
                            // Await for the editor panel to be fully updated
                            // as some buttons of the link popover we create
                            // here relies on clicking in that editor panel...
                            await this.snippetsMenu._mutex.exec(() => null);
                        }
                        this.linkPopover = await weWidgets.LinkPopoverWidget.createFor(this, $target[0], { wysiwyg: this });
                        $target.data('popover-widget-initialized', this.linkPopover);
                    })();
                }
                $target.focus();
                if ($target.closest('#wrapwrap').length) {
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

        return _super.apply(this, arguments).then(() => {
            if (this.options.autohideToolbar) {
                if (this.odooEditor.isMobile) {
                    $(this.odooEditor.editable).before(this.toolbar.$el);
                } else {
                    $(document.body).append(this.toolbar.$el);
                }
            }
        });
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

        const startCollaborationTime = new Date().getTime();

        // No need for secure random number.
        const currentClientId = Math.floor(Math.random() * Math.pow(2, 52)).toString();

        this._collaborationChannelName = channelName;
        Wysiwyg.activeCollaborationChannelNames.add(channelName);

        this.call('bus_service', 'onNotification', this, (notifications) => {
            for (const { payload, type } of notifications) {
                if (
                    type === 'editor_collaboration' &&
                    payload.model_name === modelName &&
                    payload.field_name === fieldName &&
                    payload.res_id === resId
                ) {
                    this._peerToPeerLoading.then(() => this.ptp.handleNotification(payload));
                }
            }
        });
        this.call('bus_service', 'addChannel', this._collaborationChannelName);
        this.call('bus_service', 'startPolling');

        // Wether or not the history has been sent or received at least once.
        let historySyncAtLeastOnce = false;
        let historySyncFinished = false;
        // const syncHistory = async (fromClientId) => {
        // }
        // Check wether clientA is before clientB.
        const isClientFirst = (clientA, clientB) => {
            if (clientA.startTime === clientB.startTime) {
                return clientA.id.localCompare(clientB.id) === -1;
            } else {
                return clientA.startTime < clientB.startTime;
            }
        };
        const rpcMutex = new Mutex();

        this._peerToPeerLoading = new Promise(async (resolve) => {
            let iceServers = await this._rpc({route: '/web_editor/get_ice_servers'});
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

            this.ptp = new PeerToPeer({
                peerConnectionConfig: { iceServers },
                currentClientId: currentClientId,
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
                    get_start_time: () => startCollaborationTime,
                    get_client_name: async () => {
                        if (!this._userName) {
                            this._userName = (await this._rpc({
                                model: "res.users",
                                method: "search_read",
                                args: [
                                    [['id', '=', this.getSession().user_id]],
                                    ['name']
                                ],
                            }))[0].name;
                        }
                        return this._userName;
                    },
                    get_missing_steps: (params) => this.odooEditor.historyGetMissingSteps(params.requestPayload),
                    get_history_from_snapshot: () => this.odooEditor.historyGetSnapshotSteps(),
                    get_collaborative_selection: () => this.odooEditor.getCurrentCollaborativeSelection(),
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
                            this.ptp.clientsInfos[fromClientId].startTime = await this.ptp.requestClient(fromClientId, 'get_start_time', undefined, { transport: 'rtc' });
                            this.ptp.requestClient(fromClientId, 'get_client_name', undefined, { transport: 'rtc' }).then((clientName) => {
                                this.ptp.clientsInfos[fromClientId].clientName = clientName;
                            });

                            if (!historySyncAtLeastOnce) {
                                historySyncAtLeastOnce = true;
                                await editorCollaborationOptions.onHistoryNeedSync();
                                historySyncFinished = true;
                            } else {
                                const remoteSelection = await this.ptp.requestClient(fromClientId, 'get_collaborative_selection', undefined, { transport: 'rtc' });
                                if (remoteSelection) {
                                    this.odooEditor.onExternalMultiselectionUpdate(remoteSelection);
                                }
                            }
                            break;
                        }
                        case 'oe_history_step':
                            // Avoid race condition where the step is received
                            // before the history has synced at least once.
                            if (historySyncFinished) {
                                this.odooEditor.onExternalHistorySteps([notificationPayload]);
                            }
                            break;
                        case 'oe_history_set_selection': {
                            const client = this.ptp.clientsInfos[fromClientId];
                            if (!client) {
                                return;
                            }
                            const selection = notificationPayload;
                            selection.clientName = client.clientName;
                            this.odooEditor.onExternalMultiselectionUpdate(selection);
                            break;
                        }
                    }
                }
            });
            resolve();
        });

        const editorCollaborationOptions = {
            collaborationClientId: currentClientId,
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
                const missingSteps = await this.ptp.requestClient(
                    step.clientId,
                    'get_missing_steps', {
                        fromStepId: fromStepId,
                        toStepId: step.id
                    },
                    { transport: 'rtc' }
                );
                if (missingSteps === -1 || !missingSteps.length) {
                    // This case should never happen.
                    console.warn('Editor get_missing_steps result is erroneous.');
                    return;
                }
                this.ptp && this.odooEditor.onExternalHistorySteps(missingSteps.concat([step]));
            },
            onHistoryNeedSync: async () => {
                if (!this.ptp) return;
                let firstClientId = currentClientId;
                let firstClientStartTime = startCollaborationTime;
                const connectedClientIds = this.ptp.getConnectedClientIds();
                for (const clientId of connectedClientIds) {
                    const clientInfo = this.ptp.clientsInfos[clientId];
                    // Ensure we already retreived remote client starting time.
                    if (!clientInfo.startTime) {
                        continue;
                    }

                    const isCurrentClientFirst = isClientFirst(
                        {
                            startTime: clientInfo.startTime,
                            id: clientId,
                        },
                        {
                            startTime: firstClientStartTime,
                            id: firstClientId,
                        }
                    );

                    if (isCurrentClientFirst) {
                        firstClientStartTime = clientInfo.startTime;
                        firstClientId = clientId;
                    }
                }

                if (firstClientId !== currentClientId) {
                    const historySteps = await this.ptp.requestClient(firstClientId, 'get_history_from_snapshot', undefined, { transport: 'rtc' });
                    this.odooEditor.historyResetFromSteps(historySteps);
                    const remoteSelection = await this.ptp.requestClient(firstClientId, 'get_collaborative_selection', undefined, { transport: 'rtc' });
                    if (remoteSelection) {
                        this.odooEditor.onExternalMultiselectionUpdate(remoteSelection);
                    }
                }
            },
        };
        return editorCollaborationOptions;
    },
    /**
     * @override
     */
    destroy: function () {
        if (this._collaborationChannelName) {
            Wysiwyg.activeCollaborationChannelNames.delete(this._collaborationChannelName);
        }

        if (this.odooEditor) {
            this.odooEditor.document.removeEventListener('selectionchange', this._onSelectionChange);
            this.odooEditor.destroy();
        }
        // If peer to peer is initializing, wait for properly closing it.
        if (this._peerToPeerLoading) {
            this._peerToPeerLoading.then(()=> {
                this.call('bus_service', 'deleteChannel', this._collaborationChannelName);
                this.ptp.closeAllConnections();
            });
        }
        this.$editable && this.$editable.off('blur', this._onBlur);
        document.removeEventListener('mousedown', this._onDocumentMousedown, true);
        const $body = $(document.body);
        $body.off('mousemove', this.resizerMousemove);
        $body.off('mouseup', this.resizerMouseup);
        const $wrapwrap = $('#wrapwrap');
        if ($wrapwrap.length) {
            $('#wrapwrap')[0].removeEventListener('scroll', this.odooEditor.multiselectionRefresh, { passive: true });
        }
        $(this.$root).off('mousedown');
        if (this.linkPopover) {
            this.linkPopover.hide();
        }
        window.removeEventListener('beforeunload', this._onBeforeUnload);
        this._super();
    },
    /**
     * @override
     */
    renderElement: function () {
        this.$editable = this.options.editable || $('<div class="note-editable">');
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
            this._replaceElement(this.$editable);
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
        return this._value !== (this.$editable.html() || this.$editable.val());
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
        $editable.find('[data-original-title=""]').removeAttr('data-original-title');
        $editable.find('a.o_image, span.fa, i.fa').html('');
        $editable.find('[aria-describedby]').removeAttr('aria-describedby').removeAttr('data-original-title');
        this.odooEditor.cleanForSave($editable[0]);
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
        return Promise.resolve({isDirty:isDirty, html:html});
    },
    /**
     * Save the content for the normal mode or the translation mode.
     */
    saveContent: async function (reload = true) {
        await this.saveToServer(reload);
    },
    /**
     * Reset the history.
     */
    historyReset: function () {
        this.odooEditor.historyReset();
    },

    /**
     * Save the content to the server for the normal mode.
     */
    saveToServer: async function (reload = true) {
        const defs = [];
        this.trigger_up('edition_will_stopped');
        this.trigger_up('ready_to_save', {defs: defs});
        await Promise.all(defs);

        this._cleanForSave();

        if (this.snippetsMenu) {
            await this.snippetsMenu.cleanForSave();
        }

        const editables = this.options.getContentEditableAreas();
        await this.saveModifiedImages(editables.length ? $(editables) : this.$editable);
        await this._saveViewBlocks();

        this.trigger_up('edition_was_stopped');
        window.removeEventListener('beforeunload', this._onBeforeUnload);
        if (reload) {
            window.location.reload();
        }
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
            const {oeModel: resModel, oeId: resId} = editableEl.dataset;
            const proms = [...editableEl.querySelectorAll('.o_modified_image_to_save')].map(async el => {
                const isBackground = !el.matches('img');
                el.classList.remove('o_modified_image_to_save');
                // Modifying an image always creates a copy of the original, even if
                // it was modified previously, as the other modified image may be used
                // elsewhere if the snippet was duplicated or was saved as a custom one.
                const newAttachmentSrc = await this._rpc({
                    route: `/web_editor/modify_image/${el.dataset.originalId}`,
                    params: {
                        res_model: resModel,
                        res_id: parseInt(resId),
                        data: (isBackground ? el.dataset.bgSrc : el.getAttribute('src')).split(',')[1],
                        mimetype: el.dataset.mimetype,
                        name: (el.dataset.fileName ? el.dataset.fileName : null),
                    },
                });
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
        this.$editable.html(value);
        this.odooEditor.sanitize();
        this.odooEditor.historyStep(true);
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
        if (this.odooEditor && !this.odooEditor.historyResetLatestComputedSelection()) {
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
        };
        if (this.odooFieldObservers) {
            for (let observerData of this.odooFieldObservers) {
                observerData.observer.observe(observerData.field, observerOptions);
            }
        } else {
            const odooFieldSelector = '[data-oe-model], [data-oe-translation-id]';
            const $odooFields = this.$editable.find(odooFieldSelector);
            this.odooFieldObservers = [];

            $odooFields.each((i, field) => {
                const observer = new MutationObserver(() => {
                    let $node = $(field);
                    let $nodes = $odooFields.filter(function () {
                        return this !== field;
                    });
                    if ($node.data('oe-model')) {
                        $nodes = $nodes.filter('[data-oe-model="' + $node.data('oe-model') + '"]')
                            .filter('[data-oe-id="' + $node.data('oe-id') + '"]')
                            .filter('[data-oe-field="' + $node.data('oe-field') + '"]');
                    }

                    if ($node.data('oe-translation-id')) {
                        $nodes = $nodes.filter('[data-oe-translation-id="' + $node.data('oe-translation-id') + '"]');
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
                    $nodes.html($node.html());
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
        if (linkEl && !linkEl.matches(this.customizableLinksSelector)) {
            return;
        }
        if (this.snippetsMenu && !options.forceDialog) {
            if (options.forceOpen || !this.linkTools) {
                const $btn = this.toolbar.$el.find('#create-link');
                if (!this.linkTools || ![options.link, ...wysiwygUtils.ancestors(options.link)].includes(this.linkTools.$link[0])) {
                    const linkToolsData = Object.assign({}, this.options.defaultDataForLinkTools);
                    this.linkTools = new weWidgets.LinkTools(this, {wysiwyg: this, noFocusUrl: options.noFocusUrl}, this.odooEditor.editable, linkToolsData, $btn, options.link || this.lastMediaClicked);
                }
                this.linkTools.noFocusUrl = options.noFocusUrl;
                const _onMousedown = ev => {
                    if (
                        !ev.target.closest('.oe-toolbar') &&
                        !ev.target.closest('.ui-autocomplete') &&
                        (!this.linkTools || ![ev.target, ...wysiwygUtils.ancestors(ev.target)].includes(this.linkTools.$link[0]))
                    ) {
                        // Destroy the link tools on click anywhere outside the
                        // toolbar if the target is the orgiginal target not in the original target.
                        this.linkTools && this.linkTools.destroy();
                        this.linkTools = undefined;
                        this.odooEditor.document.removeEventListener('mousedown', _onMousedown, true);
                    }
                };
                this.odooEditor.document.addEventListener('mousedown', _onMousedown, true);
                if (!this.linkTools.$el) {
                    this.linkTools.appendTo(this.toolbar.$el);
                }
            } else {
                this.linkTools.destroy();
                this.linkTools = undefined;
            }
        } else {
            const linkDialog = new weWidgets.LinkDialog(this, {
                forceNewWindow: this.options.linkForceNewWindow,
                wysiwyg: this,
            }, this.$editable[0], {
                needLabel: true,
            }, undefined, options.link);
            const restoreSelection = preserveCursor(this.odooEditor.document);
            linkDialog.open();
            linkDialog.on('save', this, data => {
                if (!data) {
                    return;
                }
                const linkWidget = linkDialog.linkWidget;
                getDeepRange(this.$editable[0], {range: data.range, select: true});
                if (!linkWidget.$link.length) {
                    linkWidget.$link = $(linkWidget.getOrCreateLink(this.$editable[0]));
                }
                if (this.options.userGeneratedContent) {
                    data.rel = 'ugc';
                }
                linkWidget.applyLinkToDom(data);
                this.odooEditor.historyStep();
                // At this point, the dialog is still open and prevents the
                // focus in the editable, even though that is where the
                // selection is. This waits so the dialog is destroyed when we
                // set the focus.
                setTimeout(() => this.odooEditor.document.getSelection().collapseToEnd(), 0);
            });
            linkDialog.on('closed', this, function () {
                // If the linkDialog content has been saved
                // the previous selection in not relevant anymore.
                if (linkDialog.destroyAction !== 'save') {
                    restoreSelection();
                }
            });
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
        const fontawesomeIcon = getInSelection(this.odooEditor.document, '.fa');
        if (fontawesomeIcon && sel.toString().trim() === "") {
            params.node = $(fontawesomeIcon);
            // save layouting classes from icons to not break the page if you edit an icon
            params.htmlClass = [...fontawesomeIcon.classList].filter((className) => {
                return !className.startsWith('fa') || faZoomClassRegex.test(className);
            }).join(' ');
        }
        if (!sel.rangeCount) {
            return;
        }
        const range = sel.getRangeAt(0);
        // We lose the current selection inside the content editable when we
        // click the media dialog button so we need to be able to restore the
        // selection when the modal is closed.
        const restoreSelection = preserveCursor(this.odooEditor.document);

        const $node = $(params.node);
        // We need to keep track of FA icon because media.js will _clear those classes
        const wasFontAwesome = $node.hasClass('fa');
        const $editable = $(this.odooEditor.editable);
        const model = $editable.data('oe-model');
        const field = $editable.data('oe-field');
        const type = $editable.data('oe-type');

        const mediaParams = Object.assign({
            res_model: model,
            res_id: $editable.data('oe-id'),
            domain: $editable.data('oe-media-domain'),
            useMediaLibrary: field && (model === 'ir.ui.view' && field === 'arch' || type === 'html'),
        }, this.options.mediaModalParams, params);
        const mediaDialog = new weWidgets.MediaDialog(this, mediaParams, $node);
        mediaDialog.open();

        mediaDialog.on('save', this, function (element) {
            if (!element) {
                return;
            }
            // restore saved html classes
            if (params.htmlClass) {
                element.className += " " + params.htmlClass;
            }
            restoreSelection();
            if (wysiwygUtils.isImg($node[0]) || wasFontAwesome) {
                $node.replaceWith(element);
                this.odooEditor.unbreakableStepUnactive();
                this.odooEditor.historyStep();
            } else if (element) {
                this.odooEditor.execCommand('insertHTML', element.outerHTML);
            }
        });
        mediaDialog.on('closed', this, function () {
            // if the mediaDialog content has been saved
            // the previous selection in not relevant anymore
            if (mediaDialog.destroyAction !== 'save') {
                restoreSelection();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        $toolbar.find('.btn-group').on('mousedown', e => e.preventDefault());
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
                    this.openMediaDialog();
                    break;
                case 'media-description':
                    new weWidgets.AltDialog(this, {}, this.lastMediaClicked).open();
                    break;
            }
        };
        if (!this.options.snippets) {
            $toolbar.find('#justify, #table, #media-insert').remove();
        }
        $toolbar.find('#create-link, #media-insert, #media-replace, #media-description').click(openTools);
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
            this.lastMediaClicked.classList.remove('float-left', 'float-right');
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
            new weWidgets.ImageCropWidget(this, this.lastMediaClicked).appendTo(this.$editable);
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
        // we need the Timeout to be sure the editable content is loaded
        // before calculating the scrollParent() element.
        setTimeout(() => {
            const scrollableContainer = this.$el.scrollParent();
            if (!options.snippets && scrollableContainer.length) {
                // this.odooEditor.addDomListener(
                //   scrollableContainer[0],
                //   'scroll',
                //   this.odooEditor.updateToolbarPosition.bind(this.odooEditor),
                // );
            }
        }, 0);
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
                return !(ev.clickEvent && ev.clickEvent.originalEvent && ev.clickEvent.originalEvent.__isColorpickerClick);
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
                    colorpicker = new ColorPaletteWidget(this, {
                        excluded: ['transparent_grayscale'],
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
                        this._processAndApplyColor(eventName, ev.data.color);
                        this._updateEditorUI();
                    });
                    colorpicker.on('color_hover', null, ev => {
                        if (hadNonCollapsedSelection) {
                            this.odooEditor.historyResetLatestComputedSelection(true);
                        }
                        this.odooEditor.historyPauseSteps();
                        try {
                            this._processAndApplyColor(eventName, ev.data.color);
                        } finally {
                            this.odooEditor.historyUnpauseSteps();
                        }
                    });
                    colorpicker.on('color_leave', null, ev => {
                        this.odooEditor.historyRevertCurrentStep();
                    });
                    colorpicker.on('enter_key_color_colorpicker', null, () => {
                        $dropdown.children('.dropdown-toggle').dropdown('hide');
                    });
                    return colorpicker.replace(hookEl).then(() => {
                        if (oldColorpicker) {
                            oldColorpicker.destroy();
                        }
                        manualOpening = true;
                        $dropdown.children('.dropdown-toggle').dropdown('show');
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
    _processAndApplyColor: function (eventName, color) {
        if (!color) {
            color = 'inherit';
        } else if (!ColorpickerWidget.isCSSColor(color) && !weUtils.isColorGradient(color)) {
            color = (eventName === "foreColor" ? 'text-' : 'bg-') + color;
        }
        this.odooEditor.execCommand('applyColor', color, eventName === 'foreColor' ? 'color' : 'backgroundColor', this.lastMediaClicked);
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
        if (e && e.key === 'k' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            const targetEl = this.odooEditor.document.getSelection().getRangeAt(0).startContainer;
            // Link tool is different if the selection is an image or a text.
            if (targetEl instanceof HTMLElement
                    && (targetEl.tagName === 'IMG' || targetEl.querySelectorAll('img').length === 1)) {
                core.bus.trigger('activate_image_link_tool');
                return;
            }
            this.toggleLinkTools();
        }
        // Override selectAll (CTRL+A) to restrict it to the editable zone / current snippet and prevent traceback.
        if (e && e.key === 'a' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            const selection = this.odooEditor.document.getSelection();
            const containerSelector = '#wrap>*, [contenteditable], .oe_structure>*';
            let $deepestParent =
                selection ?
                    $(selection.anchorNode).parentsUntil(containerSelector).last() :
                    $();

            if ($deepestParent.is('html')) {
                // In case we didn't find a suitable container
                // we need to restrict the selection inside to the editable area.
                $deepestParent = this.$editable.find(containerSelector);
            }

            if ($deepestParent.length) {
                const range = document.createRange();
                range.selectNodeContents($deepestParent.parent()[0]);
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }
    },
    /**
     * Update any editor UI that is not handled by the editor itself.
     */
    _updateEditorUI: function (e) {
        this.odooEditor.automaticStepSkipStack();
        // We need to use the editor's window so the tooltip displays in its
        // document even if it's in an iframe.
        const editorWindow = this.odooEditor.document.defaultView;
        const $target = e ? editorWindow.$(e.target) : editorWindow.$();
        // Restore paragraph dropdown button's default ID.
        this.toolbar.$el.find('#mediaParagraphDropdownButton').attr('id', 'paragraphDropdownButton');
        // Hide the create-link button if the selection spans several blocks.
        const selection = this.odooEditor.document.getSelection();
        const range = selection.rangeCount && selection.getRangeAt(0);
        const $rangeContainer = range && $(range.commonAncestorContainer);
        const spansBlocks = range && !!$rangeContainer.contents().filter((i, node) => isBlock(node)).length;
        this.toolbar.$el.find('#create-link').toggleClass('d-none', !range || spansBlocks);
        // Only show the media tools in the toolbar if the current selected
        // snippet is a media.
        const isInMedia = $target.is(mediaSelector);
        this.toolbar.$el.find([
            '#image-shape',
            '#image-width',
            '#image-padding',
            '#image-edit',
            '#media-replace',
        ].join(',')).toggleClass('d-none', !isInMedia);
        // The image replace button is in the image options when the sidebar
        // exists.
        if (this.snippetsMenu && $target.is('img')) {
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
            // Always hide the unlink button on media.
            this.toolbar.$el.find('#unlink').toggleClass('d-none', true);
            // Show the floatingtoolbar on the topleft of the media.
            if (this.options.autohideToolbar) {
                const imagePosition = this.lastMediaClicked.getBoundingClientRect();
                this.toolbar.$el.css({
                    visibility: 'visible',
                    top: imagePosition.top + 10 + 'px',
                    left: imagePosition.left + 10 + 'px',
                });
            }
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
        const link = getInSelection(this.odooEditor.document, this.customizableLinksSelector);
        if (isInMedia || link) {
            // Handle the media/link's tooltip.
            this.showTooltip = true;
            setTimeout(() => {
                // Do not show tooltip on double-click and if there is already one
                if (!this.showTooltip || $target.attr('title') !== undefined) {
                    return;
                }
                this.odooEditor.observerUnactive();
                $target.tooltip({title: _t('Double-click to edit'), trigger: 'manual', container: 'body'}).tooltip('show');
                this.odooEditor.observerActive();
                setTimeout(() => $target.tooltip('dispose'), 800);
            }, 400);
        }
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
                ['float-left', 'justifyLeft'],
                ['mx-auto', 'justifyCenter'],
                ['float-right', 'justifyRight'],
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
            resetAlignment = !['float-left', 'mx-auto', 'float-right'].some(className => (
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
    _editorOptions: function () {
        var self = this;
        var options = Object.assign({}, this.defaultOptions, this.options);
        options.onChange = function (html, $editable) {
            $editable.trigger('content_changed');
            self.trigger_up('wysiwyg_change');
        };
        options.onUpload = function (attachments) {
            self.trigger_up('wysiwyg_attachment', attachments);
        };
        options.onFocus = function () {
            self.trigger_up('wysiwyg_focus');
        };
        options.onBlur = function () {
            self.trigger_up('wysiwyg_blur');
        };
        return options;
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
        if ($el.data('oe-translation-id')) {
            return this._rpc({
                model: 'ir.translation',
                method: 'save_html',
                args: [
                    [+$el.data('oe-translation-id')],
                    this._getEscapedElement($el).html()
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
    _cleanForSave: function () {
        this.odooEditor.clean();
        this.$editable.find('.oe_edited_link').removeClass('oe_edited_link');
    },
    _getCommands: function () {
        const commands = [
            {
                groupName: 'Basic blocks',
                title: 'Quote',
                description: 'Add a blockquote section.',
                fontawesome: 'fa-quote-right',
                callback: () => {
                    this.odooEditor.execCommand('setTag', 'blockquote');
                },
            },
            {
                groupName: 'Basic blocks',
                title: 'Code',
                description: 'Add a code section.',
                fontawesome: 'fa-code',
                callback: () => {
                    this.odooEditor.execCommand('setTag', 'pre');
                },
            },
            {
                groupName: 'Navigation',
                title: 'Link',
                description: 'Add a link.',
                fontawesome: 'fa-link',
                callback: () => {
                    this.toggleLinkTools({forceDialog: true});
                },
            },
            {
                groupName: 'Navigation',
                title: 'Button',
                description: 'Add a button.',
                fontawesome: 'fa-link',
                callback: () => {
                    this.toggleLinkTools({forceDialog: true});
                    // Force the button style after the link modal is open.
                    setTimeout(() => {
                        $(".o_link_dialog .link-style[value=primary]").click();
                    }, 150);
                },
            },
            {
                groupName: 'Medias',
                title: 'Image',
                description: 'Insert an image.',
                fontawesome: 'fa-file-image-o',
                callback: () => {
                    this.openMediaDialog();
                },
            },
            {
                groupName: 'Medias',
                title: 'Video',
                description: 'Insert a video.',
                fontawesome: 'fa-file-video-o',
                callback: () => {
                    this.openMediaDialog({noVideos: false, noImages: true, noIcons: true, noDocuments: true});
                },
            },
        ];
        if (this.options.snippets) {
            commands.push(...this._getSnippetsCommands());
        }
        return commands;
    },

    _getSnippetsCommands: function () {
        const snippetCommandCallback = (selector) => {
            const $separatorBody = $(selector);
            const $clonedBody = $separatorBody.clone().removeClass('oe_snippet_body');
            const range = getDeepRange(this.odooEditor.editable);
            const block = closestElement(range.endContainer, 'p, div, ol, ul, cl, h1, h2, h3, h4, h5, h6');
            if (block) {
                block.after($clonedBody[0]);
                this.snippetsMenu.callPostSnippetDrop($clonedBody);
            }
        };
        return [
            {
                groupName: 'Website',
                title: 'Alert',
                description: 'Insert an alert snippet.',
                fontawesome: 'fa-info',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_alert"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Rating',
                description: 'Insert a rating snippet.',
                fontawesome: 'fa-star-half-o',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_rating"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Card',
                description: 'Insert a card snippet.',
                fontawesome: 'fa-sticky-note',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_card"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Share',
                description: 'Insert a share snippet.',
                fontawesome: 'fa-share-square-o',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_share"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Text Highlight',
                description: 'Insert a text Highlight snippet.',
                fontawesome: 'fa-sticky-note',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_text_highlight"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Chart',
                description: 'Insert a chart snippet.',
                fontawesome: 'fa-bar-chart',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_chart"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Progress Bar',
                description: 'Insert a progress bar snippet.',
                fontawesome: 'fa-spinner',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_progress_bar"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Badge',
                description: 'Insert a badge snippet.',
                fontawesome: 'fa-tags',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_badge"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Blockquote',
                description: 'Insert a blockquote snippet.',
                fontawesome: 'fa-quote-left',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_blockquote"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Separator',
                description: 'Insert an horizontal separator sippet.',
                fontawesome: 'fa-minus',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_hr"]');
                },
            },
        ];
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

        const $allBlocks = $((this.options || {}).savableSelector).filter('.o_dirty');

        const $dirty = $('.o_dirty');
        $dirty
            .removeAttr('contentEditable')
            .removeClass('o_dirty oe_carlos_danger o_is_inline_editable');

        $('.o_editable')
            .removeClass('o_editable o_is_inline_editable o_editable_date_field_linked o_editable_date_field_format_changed');

        const defs = _.map($allBlocks, (el) => {
            const $el = $(el);

            $el.find('[class]').filter(function () {
                if (!this.getAttribute('class').match(/\S/)) {
                    this.removeAttribute('class');
                }
            });

            // TODO: Add a queue with concurrency limit in webclient
            return this.saving_mutex.exec(() => {
                let saveElement = '_saveElement';
                if (this.options.enableTranslation) {
                    saveElement = '_saveTranslationElement';
                }
                return this[saveElement]($el, context || weContext.get())
                .then(function () {
                    $el.removeClass('o_dirty');
                }).guardedCatch(function (response) {
                    // because ckeditor regenerates all the dom, we can't just
                    // setup the popover here as everything will be destroyed by
                    // the DOM regeneration. Add markings instead, and returns a
                    // new rejection with all relevant info
                    var id = _.uniqueId('carlos_danger_');
                    $el.addClass('o_dirty oe_carlos_danger ' + id);
                    $('.o_editable.' + id)
                        .removeClass(id)
                        .popover({
                            trigger: 'hover',
                            content: response.message.data.message || '',
                            placement: 'auto top',
                        })
                        .popover('show');
                });
            });
        });
        return Promise.all(defs).then(function () {
            window.onbeforeunload = null;
        }).guardedCatch((failed) => {
            // If there were errors, re-enable edition
            this.cancel();
            this.start();
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
    _onSelectionChange() {
        if (this.options.autohideToolbar) {
            const isVisible = this.linkPopover && this.linkPopover.el.offsetParent;
            if (isVisible && !this.odooEditor.document.getSelection().isCollapsed) {
                this.linkPopover.hide();
            }
        }
    },
    _onDocumentMousedown: function (e) {
        if (!e.target.classList.contains('o_editable_date_field_linked')) {
            this.$editable.find('.o_editable_date_field_linked').removeClass('o_editable_date_field_linked');
        }
        if (e.target.closest('.oe-toolbar')) {
            this._onToolbar = true;
        } else {
            if (this._pendingBlur && !e.target.closest('.o_wysiwyg_wrapper')) {
                this.trigger_up('wysiwyg_blur');
                this._pendingBlur = false;
            }
            this._onToolbar = false;
        }
    },
    _onBlur: function () {
        if (this._onToolbar) {
            this._pendingBlur = true;
        } else {
            this.trigger_up('wysiwyg_blur');
        }
    },
});
Wysiwyg.activeCollaborationChannelNames = new Set();
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
return Wysiwyg;
});
odoo.define('web_editor.widget', function (require) {
'use strict';
    return {
        Dialog: require('wysiwyg.widgets.Dialog'),
        MediaDialog: require('wysiwyg.widgets.MediaDialog'),
        LinkDialog: require('wysiwyg.widgets.LinkDialog'),
    };
});
