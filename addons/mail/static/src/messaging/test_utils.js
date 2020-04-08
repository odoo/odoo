odoo.define('mail.messaging.testUtils', function (require) {
'use strict';

const BusService = require('bus.BusService');

const ChatWindowService = require('mail.messaging.service.ChatWindow');
const DialogService = require('mail.messaging.service.Dialog');
const MessagingService = require('mail.messaging.service.Messaging');
const DiscussWidget = require('mail.messaging.widget.Discuss');
const MessagingMenuWidget = require('mail.messaging.widget.MessagingMenu');

const AbstractStorageService = require('web.AbstractStorageService');
const Class = require('web.Class');
const NotificationService = require('web.NotificationService');
const RamStorage = require('web.RamStorage');
const makeTestEnvironment = require('web.test_env');
const {
    createView,
    makeTestPromise,
    mock: {
        addMockEnvironment,
        patch: legacyPatch,
        unpatch: legacyUnpatch,
    },
} = require('web.test_utils');
const Widget = require('web.Widget');

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

const MockMailService = Class.extend({
    bus_service() {
        return BusService.extend({
            _beep() {}, // Do nothing
            _poll() {}, // Do nothing
            isOdooFocused() {
                return true;
            },
            updateOption() {},
        });
    },
    chat_window(isDebug = false) {
        return ChatWindowService.extend({
            _getParentNode() {
                return document.querySelector(isDebug ? 'body' : '#qunit-fixture');
            },
            _listenHomeMenu: () => {},
        });
    },
    dialog(isDebug = false) {
        return DialogService.extend({
            _getParentNode() {
                return document.querySelector(isDebug ? 'body' : '#qunit-fixture');
            },
            _listenHomeMenu: () => {},
        });
    },
    local_storage() {
        return AbstractStorageService.extend({ storage: new RamStorage() });
    },
    messaging() {
        return MessagingService.extend();
    },
    notification() {
        return NotificationService;
    },
    getServices({
        hasChatWindow = false,
        isDebug = false,
    }) {
        const services = {
            bus_service: this.bus_service(),
            dialog: this.dialog(isDebug),
            local_storage: this.local_storage(),
            messaging: this.messaging(),
            notification: this.notification(),
        };
        if (hasChatWindow) {
            Object.assign(services, {
                chat_window: this.chat_window(isDebug),
            });
        }
        return services;
    },
});

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
        mount: prevMount.concat(({ widget }) => {
            // trigger mounting of chat window manager
            widget.call('chat_window', '_onWebClientReady');
        }),
        destroy: prevDestroy.concat(({ widget }) => {
            widget.call('chat_window', 'destroy');
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
function _useDiscuss(callbacks) {
    const {
        init: prevInit,
        mount: prevMount,
        destroy: prevDestroy,
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
        destroy: prevDestroy.concat(({ widget }) => {
            widget.call('chat_window', 'destroy');
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
        destroy: prevDestroy,
        return: prevReturn,
    } = callbacks;
    let messagingMenuWidget;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(async ({ selector, widget }) => {
            messagingMenuWidget = new MessagingMenuWidget(widget, {});
            await messagingMenuWidget.appendTo($(selector));
            messagingMenuWidget.on_attach_callback();
        }),
        destroy: prevDestroy.concat(({ widget }) => {
            widget.call('chat_window', 'destroy');
        }),
        return: prevReturn.concat(result => {
            Object.assign(result, { messagingMenuWidget });
        }),
    });
}

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

/**
 * @param {Object} [param0={}]
 * @param {boolean} [hasChatWindow]
 * @param {boolean} [isDebug]
 * @returns {Object}
 */
function getServices({ hasChatWindow, isDebug } = {}) {
    return new MockMailService().getServices({ hasChatWindow, isDebug });
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
    let requestAnimationFrame = owl.Component.scheduler.requestAnimationFrame;
    return new Promise(function (resolve) {
        setTimeout(() => requestAnimationFrame(() => resolve()));
    });
}

/**
 * Returns a promise resolved the next time OWL stops rendering.
 *
 * @param {function} [func=() => {}] function which, when called, is
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

    async function afterNextRender(func = () => {}, timeoutDelay = 5000) {
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
            await afterNextRender(undefined, timeoutDelay);
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
            partner_root: [2, "OdooBot"],
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
            },
            records: [],
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

async function pause() {
    await new Promise(() => {});
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
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasChatWindow=false] if set, mount chat window
 *   service.
 * @param {boolean} [param0.hasDiscuss=false] if set, mount discuss app.
 * @param {boolean} [param0.hasMessagingMenu=false] if set, mount messaging
 *   menu.
 * @param {boolean} [param0.hasView=false] if set, use createView to create a
 *   view instead of a generic widget.
 * @param {Object} [param0.messagingEnvExtension]
 * @param {string} [param0.model] makes only sense when `param0.hasView` is set:
 *   the model to use in createView.
 * @param {integer} [param0.res_id] makes only sense when `param0.hasView` is set:
 *   the res_id to use in createView.
 * @param {Object} [param0.services]
 * @param {Object} [param0.session={}]
 * @param {string} [param0.session.name="Admin"]
 * @param {integer} [param0.session.partner_id=3]
 * @param {string} [param0.session.partner_display_name="Your Company, Admin"]
 * @param {integer} [param0.session.uid=2]
 * @param {Object} [param0.View] makes only sense when `param0.hasView` is set:
 *   the View class to use in createView.
 * @param {Object} [param0.viewOptions] makes only sense when `param0.hasView`
 *   is set: the view options to use in createView.
 * @param {boolean} [param0.waitUntilMessagingInitialized=true]
 * @param {integer} [param0.'window.innerHeight']
 * @param {integer} [param0.'window.innerWidth']
 * @param {Object} [param0.'window.Notification']
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
        hasChatWindow = false,
        hasDiscuss = false,
        hasMessagingMenu = false,
        hasView = false,
        waitUntilMessagingInitialized = true,
    } = param0;
    delete param0.hasChatWindow;
    delete param0.hasDiscuss;
    delete param0.hasMessagingMenu;
    delete param0.hasView;
    if (hasChatWindow) {
        callbacks = _useChatWindow(callbacks);
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
    const {
        messagingEnvExtension,
        services = getServices({ hasChatWindow, debug }),
        session = {},
        'window.innerHeight': windowInnerHeight,
        'window.innerWidth': windowInnerWidth,
        'window.Notification': windowNotification,
    } = param0;
    initCallbacks.forEach(callback => callback(param0));
    const kwargs = Object.assign({
        archs: { 'mail.message,false,search': '<search/>' },
        debug,
        services,
        session,
    }, param0);
    _.defaults(session, {
        name: "Admin",
        partner_id: 3,
        partner_display_name: "Your Company, Admin",
        uid: 2,
    });
    const {
        messagingCreatedPromise,
        messagingInitializedPromise,
        unpatch: unpatchMessagingService,
    } = patchMessagingService(services.messaging, {
        messagingEnvExtension,
        session,
        'window.innerHeight': windowInnerHeight,
        'window.innerWidth': windowInnerWidth,
        'window.Notification': windowNotification,
    });

    let widget;
    const selector = debug ? 'body' : '#qunit-fixture';
    if (hasView) {
        widget = await createView(kwargs);
        legacyPatch(widget, {
            destroy() {
                this._super(...arguments);
                destroyCallbacks.forEach(callback => callback({ widget }));
                unpatchMessagingService();
                legacyUnpatch(widget);
            }
        });
    } else {
        const Parent = Widget.extend({ do_push_state() {} });
        const parent = new Parent();
        addMockEnvironment(parent, kwargs);
        widget = new Widget(parent);
        await widget.appendTo($(selector));
        Object.assign(widget, {
            destroy() {
                delete widget.destroy;
                destroyCallbacks.forEach(callback => callback({ widget }));
                parent.destroy();
                unpatchMessagingService();
            },
        });
    }
    await messagingCreatedPromise;
    if (waitUntilMessagingInitialized) {
        await messagingInitializedPromise;
    }

    await Promise.all(mountCallbacks.map(callback => callback({ selector, widget })));
    if (hasChatWindow || hasDiscuss || hasMessagingMenu) {
        await afterNextRender();
    }
    const env = widget.call('messaging', 'getEnv');
    const result = { env, widget };
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

/**
 * @param {mail.messaging.service.Messaging} MessagingService
 * @param {Object} [param1={}]
 * @param {Object} [param1.messagingEnvExtension]
 * @param {Object} [param1.session={}]
 * @param {integer} [param1.'window.innerHeight'=1080]
 * @param {integer} [param1.'window.innerWidth'=1920]
 * @param {Object} [param1.'window.Notification']
 * @returns {Object}
 *   - `messagingCreatedPromise`, a promise that is resolved just after
 *     messaging has been created.
 *   - `messagingInitializedPromise`, a promise that is resolved just after
 *     messaging has been initialized.
 *   - `unpatch`, to unpatch messaging service.
 */
function patchMessagingService(MessagingService, {
    messagingEnvExtension,
    session = {},
    'window.innerHeight': windowInnerHeight,
    'window.innerWidth': windowInnerWidth,
    'window.Notification': windowNotification,
} = {}) {
    const _t = s => s;
    _t.database = {
        parameters: { direction: 'ltr' },
    };
    const messagingCreatedPromise = makeTestPromise();
    const messagingInitializedPromise = makeTestPromise();
    const env = {
        _t,
        session: Object.assign({
            is_bound: Promise.resolve(),
            name: 'Admin',
            partner_display_name: 'Mitchell Admin',
            partner_id: 3,
            url: s => s,
            userId: 2,
        }, session),
        window: {},
    };
    if (windowInnerHeight) {
        env.window.innerHeight = windowInnerHeight;
    }
    if (windowInnerWidth) {
        env.window.innerWidth = windowInnerWidth;
    }
    if (windowNotification) {
        env.window.Notification = windowNotification;
    }
    legacyPatch(MessagingService, {
        env: makeTestEnvironment(env),
        messagingEnvExtension: Object.assign({
            autofetchPartnerImStatus: false,
            disableAnimation: true,
        }, messagingEnvExtension),
        start(...args) {
            this._super(...args);
            // simulate all JS resources have been loaded
            const {
                messagingCreatedPromise: createdPromise,
                messagingInitializedPromise: initializedPromise,
            } = this._onGlobalLoad();
            createdPromise.then(() => messagingCreatedPromise.resolve());
            initializedPromise.then(() => messagingInitializedPromise.resolve());
        },
        _listenGlobalWindowLoad() {},
    });
    const unpatchMessagingService = () => legacyUnpatch(MessagingService);
    return {
        messagingCreatedPromise,
        messagingInitializedPromise,
        unpatch: unpatchMessagingService,
    };
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
    getServices,
    inputFiles,
    nextAnimationFrame,
    pasteFiles,
    patchMessagingService,
    pause,
    start,
};

});
