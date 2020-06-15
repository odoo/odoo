odoo.define('mail/static/src/utils/test_utils.js', function (require) {
'use strict';

const BusService = require('bus.BusService');

const {
    addMessagingToEnv,
    addTimeControlToEnv,
} = require('mail/static/src/env/test_env.js');
const ChatWindowService = require('mail/static/src/services/chat_window_service/chat_window_service.js');
const DialogService = require('mail/static/src/services/dialog_service/dialog_service.js');
const { nextTick } = require('mail/static/src/utils/utils.js');
const DiscussWidget = require('mail/static/src/widgets/discuss/discuss.js');
const MessagingMenuWidget = require('mail/static/src/widgets/messaging_menu/messaging_menu.js');

const AbstractStorageService = require('web.AbstractStorageService');
const NotificationService = require('web.NotificationService');
const RamStorage = require('web.RamStorage');
const {
    createActionManager,
    createView,
    makeTestPromise,
    mock: {
        addMockEnvironment,
        patch: legacyPatch,
        unpatch: legacyUnpatch,
    },
} = require('web.test_utils');
const Widget = require('web.Widget');

const { Component } = owl;

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * Create a fake object 'dataTransfer', linked to some files,
 * which is passed to drag and drop events.
 *
 * @param {Object[]} files
 * @returns {Object}
 */
function _createFakeDataTransfer(files) {
    return {
        dropEffect: 'all',
        effectAllowed: 'all',
        files,
        items: [],
        types: ['Files'],
    };
}

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @returns {Object} update callbacks
 */
function _useChatWindow(callbacks) {
    const {
        mount: prevMount,
        destroy: prevDestroy,
    } = callbacks;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(() => {
            // trigger mounting of chat window manager
            Component.env.services['chat_window']._onWebClientReady();
        }),
        destroy: prevDestroy.concat(() => {
            Component.env.services['chat_window'].destroy();
        }),
    });
}

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @returns {Object} update callbacks
 */
function _useDialog(callbacks) {
    const {
        mount: prevMount,
        destroy: prevDestroy,
    } = callbacks;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(() => {
            // trigger mounting of dialog manager
            Component.env.services['dialog']._onWebClientReady();
        }),
        destroy: prevDestroy.concat(() => {
            Component.env.services['dialog'].destroy();
        }),
    });
}

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @return {Object} update callbacks
 */
function _useDiscuss(callbacks) {
    const {
        init: prevInit,
        mount: prevMount,
        return: prevReturn,
    } = callbacks;
    let discussWidget;
    const state = {
        autoOpenDiscuss: false,
        discussData: {},
    };
    return Object.assign({}, callbacks, {
        init: prevInit.concat(params => {
            const {
                autoOpenDiscuss = state.autoOpenDiscuss,
                discuss: discussData = state.discussData
            } = params;
            Object.assign(state, { autoOpenDiscuss, discussData });
            delete params.autoOpenDiscuss;
            delete params.discuss;
        }),
        mount: prevMount.concat(async params => {
            const { selector, widget } = params;
            DiscussWidget.prototype._pushStateActionManager = () => {};
            discussWidget = new DiscussWidget(widget, state.discussData);
            await discussWidget.appendTo($(selector));
            if (state.autoOpenDiscuss) {
                discussWidget.on_attach_callback();
            }
        }),
        return: prevReturn.concat(result => {
            Object.assign(result, { discussWidget });
        }),
    });
}

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @returns {Object} update callbacks
 */
function _useMessagingMenu(callbacks) {
    const {
        mount: prevMount,
        return: prevReturn,
    } = callbacks;
    let messagingMenuWidget;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(async ({ selector, widget }) => {
            messagingMenuWidget = new MessagingMenuWidget(widget, {});
            await messagingMenuWidget.appendTo($(selector));
            messagingMenuWidget.on_attach_callback();
        }),
        return: prevReturn.concat(result => {
            Object.assign(result, { messagingMenuWidget });
        }),
    });
}

//------------------------------------------------------------------------------
// Public: rendering timers
//------------------------------------------------------------------------------

/**
 * Returns a promise resolved at the next animation frame.
 *
 * @returns {Promise}
 */
function nextAnimationFrame() {
    const requestAnimationFrame = owl.Component.scheduler.requestAnimationFrame;
    return new Promise(function (resolve) {
        setTimeout(() => requestAnimationFrame(() => resolve()));
    });
}

/**
 * Returns a promise resolved the next time OWL stops rendering.
 *
 * @param {function} func function which, when called, is
 *   expected to trigger OWL render(s).
 * @param {number} [timeoutDelay=5000] in ms
 * @returns {Promise}
 */
const afterNextRender = (function () {
    const stop = owl.Component.scheduler.stop;
    const stopPromises = [];

    owl.Component.scheduler.stop = function () {
        const wasRunning = this.isRunning;
        stop.call(this);
        if (wasRunning) {
            while (stopPromises.length) {
                stopPromises.pop().resolve();
            }
        }
    };

    async function afterNextRender(func, timeoutDelay = 5000) {
        // Define the potential errors outside of the promise to get a proper
        // trace if they happen.
        const startError = new Error("Timeout: the render didn't start.");
        const stopError = new Error("Timeout: the render didn't stop.");
        // Set up the timeout to reject if no render happens.
        let timeoutNoRender;
        const timeoutProm = new Promise((resolve, reject) => {
            timeoutNoRender = setTimeout(() => {
                let error = startError;
                if (owl.Component.scheduler.isRunning) {
                    error = stopError;
                }
                console.error(error);
                reject(error);
            }, timeoutDelay);
        });
        // Set up the promise to resolve if a render happens.
        const prom = makeTestPromise();
        stopPromises.push(prom);
        // Start the function expected to trigger a render after the promise
        // has been registered to not miss any potential render.
        const funcRes = func();
        // Make them race (first to resolve/reject wins).
        await Promise.race([prom, timeoutProm]);
        clearTimeout(timeoutNoRender);
        // Wait the end of the function to ensure all potential effects are
        // taken into account during the following verification step.
        await funcRes;
        // Wait one more frame to make sure no new render has been queued.
        await nextAnimationFrame();
        if (owl.Component.scheduler.isRunning) {
            await afterNextRender(() => {}, timeoutDelay);
        }
    }

    return afterNextRender;
})();


//------------------------------------------------------------------------------
// Public: test lifecycle
//------------------------------------------------------------------------------

function beforeEach(self) {
    const data = {
        initMessaging: {
            channel_slots: {},
            commands: [],
            is_moderator: false,
            mail_failures: [],
            mention_partner_suggestions: [],
            menu_id: false,
            moderation_counter: 0,
            moderation_channel_ids: [],
            needaction_inbox_counter: 0,
            partner_root: {
                active: false,
                display_name: "OdooBot",
                id: 2,
            },
            public_partner: {
                active: false,
                display_name: "Public user",
                id: 4,
            },
            shortcodes: [],
            starred_counter: 0,
        },
        'ir.attachment': {
            fields: {
                name: { type: 'char', string: "attachment name", required: true },
                res_model: { type: 'char', string: "res model" },
                res_id: { type: 'integer', string: "res id" },
                url: { type: 'char', string: 'url' },
                type: { type: 'selection', selection: [['url', "URL"], ['binary', "BINARY"]] },
                mimetype: { type: 'char', string: "mimetype" },
            },
        },
        'mail.activity': {
            fields: {
                can_write: {
                    type: 'boolean',
                },
                icon: {
                    type: 'string',
                },
                id: {
                    type: 'integer',
                },
                res_id: {
                    type: 'integer',
                },
                res_model: {
                    type: 'string',
                },
            },
        },
        'mail.channel': {
            fields: {
                channel_type: {
                    string: "Channel Type",
                    type: "selection",
                },
                id: {
                    string: "Id",
                    type: 'integer',
                },
                message_unread_counter: {
                    string: "# unread messages",
                    type: 'integer',
                },
                name: {
                    string: "Name",
                    type: "char",
                    required: true,
                },
            },
        },
        'mail.followers': {
            fields: {
                channel_id: {
                    type: 'integer',
                },
                email: {
                    type: 'string',
                },
                id: {
                    type: 'integer',
                },
                is_active: {
                    type: 'boolean',
                },
                is_editable: {
                    type: 'boolean',
                },
                name: {
                    type: 'string',
                },
                partner_id: {
                    type: 'integer',
                },
            },
        },
        'mail.message': {
            fields: {
                attachment_ids: {
                    string: "Attachments",
                    type: 'many2many',
                    relation: 'ir.attachment',
                    default: [],
                },
                author_id: {
                    string: "Author",
                    relation: 'res.partner',
                },
                body: {
                    string: "Contents",
                    type: 'html',
                },
                channel_ids: {
                    string: "Channels",
                    type: 'many2many',
                    relation: 'mail.channel',
                },
                date: {
                    string: "Date",
                    type: 'datetime',
                },
                history_partner_ids: {
                    string: "Partners with History",
                    type: 'many2many',
                    relation: 'res.partner',
                },
                id: {
                    string: "Id",
                    type: 'integer',
                },
                is_discussion: {
                    string: "Discussion",
                    type: 'boolean',
                },
                is_note: {
                    string: "Note",
                    type: 'boolean',
                },
                is_notification: {
                    string: "Notification",
                    type: 'boolean',
                },
                is_starred: {
                    string: "Starred",
                    type: 'boolean',
                },
                message_type: {
                    string: "Type",
                    type: 'selection',
                },
                model: {
                    string: "Related Document model",
                    type: 'char',
                },
                needaction: {
                    string: "Need Action",
                    type: 'boolean',
                },
                needaction_partner_ids: {
                    string: "Partners with Need Action",
                    type: 'many2many',
                    relation: 'res.partner',
                },
                record_name: {
                    string: "Name",
                    type: 'string',
                },
                res_id: {
                    string: "Related Document ID",
                    type: 'integer',
                },
                starred: {
                    string: "Starred",
                    type: 'boolean',
                },
                starred_partner_ids: {
                    string: "Favorited By",
                    type: 'many2many',
                    relation: 'res.partner',
                },
            },
        },
        'mail.notification': {
            fields: {
                is_read: {
                    string: "Is Read",
                    type: 'boolean',
                },
                mail_message_id: {
                    string: "Message",
                    type: 'many2one',
                    relation: 'mail.message',
                },
                res_partner_id: {
                    string: "Needaction Recipient",
                    type: 'many2one',
                    relation: 'res.partner',
                },
            },
        },
        'res.partner': {
            fields: {
                display_name: { string: "Displayed name", type: "char" },
                im_status: {
                    string: "status",
                    type: 'char',
                },
                message_follower_ids: {
                    relation: 'follower',
                    string: "Followers",
                    type: "one2many",
                },
            },
            records: [],
        },
        'res.users': {
            fields: {
                partner_id: {
                    string: "Related partners",
                    type: 'many2one',
                    relation: 'res.partner',
                },
            },
        },
    };

    const originals = {
        '_.debounce': _.debounce,
        '_.throttle': _.throttle,
        'window.fetch': window.fetch,
    };

    (function patch() {
        // patch _.debounce and _.throttle to be fast and synchronous
        _.debounce = _.identity;
        _.throttle = _.identity;
        let uploadedAttachmentsCount = 1;
        window.fetch = async function (route, form) {
            const formData = form.body;
            return {
                async text() {
                    const ufiles = formData.getAll('ufile');
                    const files = ufiles.map(ufile => JSON.stringify({
                        filename: ufile.name,
                        id: uploadedAttachmentsCount,
                        mimetype: ufile.type,
                        name: ufile.name,
                    }));
                    const callback = formData.get('callback');
                    uploadedAttachmentsCount++;
                    return `
                        <script language="javascript" type="text/javascript">
                            var win = window.top.window;
                            win.jQuery(win).trigger('${callback}', ${files.join(', ')});
                        </script>`;
                }
            };
        };
    })();

    function unpatch() {
        _.debounce = originals['_.debounce'];
        _.throttle = originals['_.throttle'];
        window.fetch = originals['window.fetch'];
    }

    Object.assign(self, { data, unpatch });

    return {
        data,
        unpatch,
    };
}

function afterEach(self) {
    self.unpatch();
}

/**
 * Main function used to make a mocked environment with mocked messaging env.
 *
 * @param {Object} [param0={}]
 * @param {string} [param0.arch] makes only sense when `param0.hasView` is set:
 *   the arch to use in createView.
 * @param {Object} [param0.archs]
 * @param {boolean} [param0.autoOpenDiscuss=false] makes only sense when
 *   `param0.hasDiscuss` is set: determine whether mounted discuss should be
 *   open initially.
 * @param {boolean} [param0.debug=false]
 * @param {Object} [param0.data] makes only sense when `param0.hasView` is set:
 *   the data to use in createView.
 * @param {Object} [param0.discuss={}] makes only sense when `param0.hasDiscuss`
 *   is set: provide data that is passed to discuss widget (= client action) as
 *   2nd positional argument.
 * @param {Object} [param0.env={}]
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasActionManager=false] if set, use
 *   createActionManager.
 * @param {boolean} [param0.hasChatWindow=false] if set, mount chat window
 *   service.
 * @param {boolean} [param0.hasDiscuss=false] if set, mount discuss app.
 * @param {boolean} [param0.hasMessagingMenu=false] if set, mount messaging
 *   menu.
 * @param {boolean} [param0.hasTimeControl=false] if set, all flow of time
 *   with `env.browser.setTimeout` are fully controlled by test itself.
 *     @see addTimeControlToEnv that adds `advanceTime` function in
 *     `env.testUtils`.
 * @param {boolean} [param0.hasView=false] if set, use createView to create a
 *   view instead of a generic widget.
 * @param {string} [param0.model] makes only sense when `param0.hasView` is set:
 *   the model to use in createView.
 * @param {integer} [param0.res_id] makes only sense when `param0.hasView` is set:
 *   the res_id to use in createView.
 * @param {Object} [param0.services]
 * @param {Object} [param0.session]
 * @param {Object} [param0.View] makes only sense when `param0.hasView` is set:
 *   the View class to use in createView.
 * @param {Object} [param0.viewOptions] makes only sense when `param0.hasView`
 *   is set: the view options to use in createView.
 * @param {boolean} [param0.waitUntilMessagingInitialized=true]
 * @param {...Object} [param0.kwargs]
 * @returns {Object}
 */
async function start(param0 = {}) {
    let callbacks = {
        init: [],
        mount: [],
        destroy: [],
        return: [],
    };
    const {
        hasActionManager = false,
        hasChatWindow = false,
        hasDialog = false,
        hasDiscuss = false,
        hasMessagingMenu = false,
        hasTimeControl = false,
        hasView = false,
        waitUntilMessagingInitialized = true,
    } = param0;
    delete param0.hasActionManager;
    delete param0.hasChatWindow;
    delete param0.hasDiscuss;
    delete param0.hasMessagingMenu;
    delete param0.hasTimeControl;
    delete param0.hasView;
    if (hasChatWindow) {
        callbacks = _useChatWindow(callbacks);
    }
    if (hasDialog) {
        callbacks = _useDialog(callbacks);
    }
    if (hasDiscuss) {
        callbacks = _useDiscuss(callbacks);
    }
    if (hasMessagingMenu) {
        callbacks = _useMessagingMenu(callbacks);
    }
    const {
        init: initCallbacks,
        mount: mountCallbacks,
        destroy: destroyCallbacks,
        return: returnCallbacks,
    } = callbacks;
    const { debug = false } = param0;
    initCallbacks.forEach(callback => callback(param0));

    let env = addMessagingToEnv(param0.env, { debug });
    if (hasTimeControl) {
        env = addTimeControlToEnv(env);
    }

    const services = Object.assign({}, {
        bus_service: BusService.extend({
            _beep() {}, // Do nothing
            _poll() {}, // Do nothing
            _registerWindowUnload() {}, // Do nothing
            isOdooFocused() {
                return true;
            },
            updateOption() {},
        }),
        chat_window: ChatWindowService.extend({
            _getParentNode() {
                return document.querySelector(debug ? 'body' : '#qunit-fixture');
            },
            _listenHomeMenu: () => {},
        }),
        dialog: DialogService.extend({
            _getParentNode() {
                return document.querySelector(debug ? 'body' : '#qunit-fixture');
            },
            _listenHomeMenu: () => {},
        }),
        local_storage: AbstractStorageService.extend({ storage: new RamStorage() }),
        notification: NotificationService.extend(),
    }, param0.services);

    const kwargs = Object.assign({}, param0, {
        archs: Object.assign({}, {
            'mail.message,false,search': '<search/>'
        }, param0.archs),
        debug: param0.debug || false,
        services: Object.assign({}, services, param0.services),
    }, { env });
    let widget;
    let mockServer; // only in basic mode
    let testEnv;
    const selector = debug ? 'body' : '#qunit-fixture';
    if (hasView) {
        widget = await createView(kwargs);
        legacyPatch(widget, {
            destroy() {
                this._super(...arguments);
                destroyCallbacks.forEach(callback => callback({ widget }));
                legacyUnpatch(widget);
                if (testEnv) {
                    testEnv.destroyMessaging();
                }
            }
        });
    } else if (hasActionManager) {
        widget = await createActionManager(kwargs);
        legacyPatch(widget, {
            destroy() {
                this._super(...arguments);
                destroyCallbacks.forEach(callback => callback({ widget }));
                legacyUnpatch(widget);
                if (testEnv) {
                    testEnv.destroyMessaging();
                }
            }
        });
    } else {
        const Parent = Widget.extend({ do_push_state() {} });
        const parent = new Parent();
        mockServer = await addMockEnvironment(parent, kwargs);
        widget = new Widget(parent);
        await widget.appendTo($(selector));
        Object.assign(widget, {
            destroy() {
                delete widget.destroy;
                destroyCallbacks.forEach(callback => callback({ widget }));
                parent.destroy();
                if (testEnv) {
                    testEnv.destroyMessaging();
                }
            },
        });
    }

    testEnv = Component.env;

    /**
     * Components cannot use web.bus, because they cannot use
     * EventDispatcherMixin, and webclient cannot easily access env.
     * Communication between webclient and components by core.bus
     * (usable by webclient) and messagingBus (usable by components), which
     * the messaging service acts as mediator since it can easily use both
     * kinds of buses.
     */
    testEnv.bus.on(
        'hide_home_menu',
        null,
        () => testEnv.messagingBus.trigger('hide_home_menu')
    );
    testEnv.bus.on(
        'show_home_menu',
        null,
        () => testEnv.messagingBus.trigger('show_home_menu')
    );
    testEnv.bus.on(
        'will_hide_home_menu',
        null,
        () => testEnv.messagingBus.trigger('will_hide_home_menu')
    );
    testEnv.bus.on(
        'will_show_home_menu',
        null,
        () => testEnv.messagingBus.trigger('will_show_home_menu')
    );
    testEnv.modelManager.start(testEnv);
    /**
     * Create the messaging singleton record.
     */
    testEnv.messaging = testEnv.models['mail.messaging'].create();
    testEnv.messaging.start().then(() =>
        testEnv.messagingInitializedDeferred.resolve()
    );

    const result = { env: testEnv, mockServer, widget };

    if (waitUntilMessagingInitialized) {
        // env key only accessible after MessagingService has started
        await testEnv.messagingInitializedDeferred;
    }

    if (mountCallbacks.length > 0) {
        await afterNextRender(async () => {
            await Promise.all(mountCallbacks.map(callback => callback({ selector, widget })));
        });
    }
    returnCallbacks.forEach(callback => callback(result));
    return result;
}

//------------------------------------------------------------------------------
// Public: file utilities
//------------------------------------------------------------------------------

/**
 * Drag some files over a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} file must have been create beforehand
 *   @see testUtils.file.createFile
 */
function dragenterFiles(el, files) {
    const ev = new Event('dragenter', { bubbles: true });
    Object.defineProperty(ev, 'dataTransfer', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
}

/**
 * Drop some files on a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
function dropFiles(el, files) {
    const ev = new Event('drop', { bubbles: true });
    Object.defineProperty(ev, 'dataTransfer', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
}

/**
 * Set files in a file input
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
function inputFiles(el, files) {
    const dataTransfer = new window.DataTransfer();
    for (const file of files) {
        dataTransfer.items.add(file);
    }
    el.files = dataTransfer.files;
    /**
     * Changing files programatically is not supposed to trigger the event but
     * it does in Chrome versions before 73 (which is on runbot), so in that
     * case there is no need to make a manual dispatch, because it would lead to
     * the files being added twice.
     */
    const versionRaw = navigator.userAgent.match(/Chrom(e|ium)\/([0-9]+)\./);
    const chromeVersion = versionRaw ? parseInt(versionRaw[2], 10) : false;
    if (!chromeVersion || chromeVersion >= 73) {
        el.dispatchEvent(new Event('change'));
    }
}

/**
 * Paste some files on a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
function pasteFiles(el, files) {
    const ev = new Event('paste', { bubbles: true });
    Object.defineProperty(ev, 'clipboardData', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

return {
    afterEach,
    afterNextRender,
    beforeEach,
    dragenterFiles,
    dropFiles,
    inputFiles,
    nextAnimationFrame,
    nextTick,
    pasteFiles,
    start,
};

});
