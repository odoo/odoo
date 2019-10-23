odoo.define('mail.owl.testUtils', function (require) {
'use strict';

const BusService = require('bus.BusService');

const ChatWindowService = require('mail.service.ChatWindow');
const OwlService = require('mail.service.Owl');
const Discuss = require('mail.widget.Discuss');
const MessagingMenu = require('mail.widget.MessagingMenu');

const AbstractStorageService = require('web.AbstractStorageService');
const Class = require('web.Class');
const NotificationService = require('web.NotificationService');
const RamStorage = require('web.RamStorage');
const { mock: { addMockEnvironment } } = require('web.test_utils');
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
    chat_window() {
        return ChatWindowService;
    },
    local_storage() {
        return AbstractStorageService.extend({ storage: new RamStorage() });
    },
    notification() {
        return NotificationService;
    },
    owl() {
        return OwlService;
    },
    getServices() {
        return {
            bus_service: this.bus_service(),
            chat_window: this.chat_window(),
            local_storage: this.local_storage(),
            notification: this.notification(),
            owl: this.owl(),
        };
    },
});

/**
 * Create a fake object 'dataTransfer', linked to some files,
 * which is passed to drag and drop events.
 *
 * @param {Object[]} files
 * @return {Object}
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

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

/**
 * @param {Object} self qunit test environment
 */
function afterEach(self) {
    // unpatch _.debounce and _.throttle
    _.debounce = self.underscoreDebounce;
    _.throttle = self.underscoreThrottle;
    window.fetch = self.ORIGINAL_WINDOW_FETCH;
}

function beforeEach(self) {
    // patch _.debounce and _.throttle to be fast and synchronous
    self.underscoreDebounce = _.debounce;
    self.underscoreThrottle = _.throttle;
    _.debounce = _.identity;
    _.throttle = _.identity;

    self.data = {
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
            shortcodes: [],
            starred_counter: 0,
        },
        'ir.attachment': {
            fields: {},
        },
        'mail.message': {
            fields: {
                body: {
                    string: "Contents",
                    type: 'html',
                },
                author_id: {
                    string: "Author",
                    relation: 'res.partner',
                },
                channel_ids: {
                    string: "Channels",
                    type: 'many2many',
                    relation: 'mail.channel',
                },
                starred: {
                    string: "Starred",
                    type: 'boolean',
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
                starred_partner_ids: {
                    string: "Favorited By",
                    type: 'many2many',
                    relation: 'res.partner',
                },
                history_partner_ids: {
                    string: "Partners with History",
                    type: 'many2many',
                    relation: 'res.partner',
                },
                model: {
                    string: "Related Document model",
                    type: 'char',
                },
                res_id: {
                    string: "Related Document ID",
                    type: 'integer',
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
                im_status: {
                    string: "status",
                    type: 'char',
                },
            },
        },
    };
    self.ORIGINAL_WINDOW_FETCH = window.fetch;
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
}

/**
 * Drag some files over a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} file must have been create beforehand
 *   @see testUtils.file.createFile
 */
async function dragenterFiles(el, files) {
    const ev = new Event('dragenter', { bubbles: true });
    Object.defineProperty(ev, 'dataTransfer', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
    await nextRender();
}

/**
 * Drop some files on a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
async function dropFiles(el, files) {
    const ev = new Event('drop', { bubbles: true });
    Object.defineProperty(ev, 'dataTransfer', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
    await nextRender();
}

function getMailServices() {
    return new MockMailService().getServices();
}

/**
 * Set files in a file input
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
async function inputFiles(el, files) {
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
    await nextRender();
}

/**
 * Wait for when OWL completely rendered UI.
 *
 * It uses request next animation frame internally.
 *
 * Note that there may be multiple rendering at the same time (e.g. thread
 * mounted loads messages, which also triggers a re-render for spinner/loaded
 * messages). Each re-render also takes a new request animation frame, so
 * waiting for next animation frame is not enough.
 *
 * In our case, 3 successive request animation frames is enough, but it may
 * be necessary to increase that amount in the future, until OWL provides
 * necessary means to detect end of rendering.
 */
async function nextRender() {
    await new Promise(resolve => setTimeout(() => window.requestAnimationFrame(() => resolve())));
    await new Promise(resolve => setTimeout(() => window.requestAnimationFrame(() => resolve())));
    await new Promise(resolve => setTimeout(() => window.requestAnimationFrame(() => resolve())));
}

/**
 * Paste some files on a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
async function pasteFiles(el, files) {
    const ev = new Event('paste', { bubbles: true });
    Object.defineProperty(ev, 'clipboardData', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
    await nextRender();
}

async function pause() {
    await new Promise(resolve => {});
}

/**
 * Create chat window manager, discuss, and messaging menu with
 * messaging store
 *
 * @param {Object} param0
 * @param {Object} [param0.archs]
 * @param {boolean} [param0.autoOpenDiscuss=false]
 * @param {boolean} [param0.debug=false]
 * @param {Object} [param0.discuss={}]
 * @param {Object} [param0.initStoreState]
 * @param {function} [param0.mockRPC]
 * @param {Object} [param0.services]
 * @param {Object} [param0.session={}]
 * @param {string} [param0.session.name="Admin"]
 * @param {integer} [param0.session.partner_id=3]
 * @param {string} [param0.session.partner_display_name="Your Company, Admin"]
 * @param {integer} [param0.session.uid=2]
 * @param {...Object} [param0.kwargs]
 * @return {Promise}
 */
async function start(param0) {
    const {
        autoOpenDiscuss = false,
        debug = false,
        discuss: discussData = {},
        initStoreState,
        services = getMailServices(),
        session = {},
    } = param0;
    const kwargs = Object.assign({
        archs: { 'mail.message,false,search': '<search/>' },
        debug,
        services,
        session,
    }, param0);
    delete kwargs.autoOpenDiscuss;
    delete kwargs.discuss;
    delete kwargs.initStoreState;
    const Parent = Widget.extend({ do_push_state() {} });
    const parent = new Parent();
    _.defaults(session, {
        name: "Admin",
        partner_id: 3,
        partner_display_name: "Your Company, Admin",
        uid: 2,
    });
    const selector = debug ? 'body' : '#qunit-fixture';
    const ORIGINAL_OWL_SERVICE_IS_TEST = services.owl.prototype.IS_TEST;
    const ORIGINAL_OWL_SERVICE_TEST_STORE_INIT_STATE = services.owl.prototype.TEST_STORE_INIT_STATE;

    const ORIGINAL_CHAT_WINDOW_SERVICE_IS_TEST = services.chat_window.prototype.IS_TEST;
    const ORIGINAL_CHAT_WINDOW_SERVICE_TEST_TARGET = services.chat_window.prototype.TEST_TARGET;

    // Enable test mode for owl service
    services.owl.prototype.IS_TEST = true;
    services.owl.prototype.TEST_STORE_INIT_STATE = initStoreState || {
        globalWindow: {
            innerHeight: 1080,
            innerWidth: 1920,
        },
        isMobile: false,
    };

    // Enable test mode for chat window service
    services.chat_window.prototype.IS_TEST = true;
    services.chat_window.prototype.TEST_TARGET = selector;

    addMockEnvironment(parent, kwargs);
    const discuss = new Discuss(parent, discussData);
    const menu = new MessagingMenu(parent, {});
    const widget = new Widget(parent);

    Object.assign(widget, {
        closeDiscuss() {
            discuss.on_detach_callback();
        },
        destroy() {
            // restore store service
            services.owl.prototype.IS_TEST = ORIGINAL_OWL_SERVICE_IS_TEST;
            services.owl.prototype.TEST_STORE_INIT_STATE = ORIGINAL_OWL_SERVICE_TEST_STORE_INIT_STATE;

            // restore chat window service
            services.chat_window.prototype.IS_TEST = ORIGINAL_CHAT_WINDOW_SERVICE_IS_TEST;
            services.chat_window.prototype.TEST_TARGET = ORIGINAL_CHAT_WINDOW_SERVICE_TEST_TARGET;

            delete widget.destroy;
            delete window.o_test_env;
            widget.call('chat_window', 'destroy');
            parent.destroy();
        },
        openDiscuss() {
            discuss.on_attach_callback();
        },
    });

    await widget.appendTo($(selector));
    const env = widget.call('owl', 'getEnv');
    if (debug) {
        window.o_test_env = env;
    }
    widget.call('chat_window', 'test:web_client_ready'); // trigger mounting of chat window manager
    await menu.appendTo($(selector));
    menu.on_attach_callback(); // trigger mounting of menu component
    await discuss.appendTo($(selector));
    if (autoOpenDiscuss) {
        widget.openDiscuss();
    }
    await nextRender();
    return { discuss, env, widget };
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

return {
    afterEach,
    beforeEach,
    dragenterFiles,
    dropFiles,
    getMailServices,
    inputFiles,
    nextRender,
    pasteFiles,
    pause,
    start,
};

});
