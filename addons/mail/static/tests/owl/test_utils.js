odoo.define('mail.owl.testUtils', function (require) {
'use strict';

const BusService = require('bus.BusService');

const ChatWindowService = require('mail.service.ChatWindowService');
const EnvService = require('mail.service.Env');
const StoreService = require('mail.service.Store');
const Discuss = require('mail.widget.Discuss');
const MessagingMenu = require('mail.widget.MessagingMenu');

const AbstractStorageService = require('web.AbstractStorageService');
const Class = require('web.Class');
const NotificationService = require('web.NotificationService');
const RamStorage = require('web.RamStorage');
const testUtils = require('web.test_utils');
const Widget = require('web.Widget');

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

const MockMailService = Class.extend({
    bus_service() {
        return BusService.extend({
            _beep() {}, // Do nothing
            _poll() {}, // Do nothing
            isOdooFocused() { return true; },
            updateOption() {},
        });
    },
    chat_window() {
        return ChatWindowService;
    },
    env() {
        return EnvService;
    },
    local_storage() {
        return AbstractStorageService.extend({
            storage: new RamStorage(),
        });
    },
    notification() {
        return NotificationService;
    },
    store_service() {
        return StoreService;
    },
    getServices() {
        return {
            bus_service: this.bus_service(),
            chat_window: this.chat_window(),
            env: this.env(),
            local_storage: this.local_storage(),
            notification: this.notification(),
            store: this.store_service(),
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
                // Needed to wait that attachment has bee nre-rendered as
                // temporary to avoid conflicting rendering
                // See https://github.com/odoo/owl/issues/268
                await testUtils.nextTick();
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
async function dragoverFiles(el, files) {
    const ev = new Event('dragover', { bubbles: true });
    Object.defineProperty(ev, 'dataTransfer', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
    await testUtils.nextTick();
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
    await testUtils.nextTick();
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
    el.dispatchEvent(new Event('change'));
    await new Promise(resolve => setTimeout(resolve, 100)); // AKU why 100ms wait???
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
    await testUtils.nextTick();
}

async function pause() {
    await new Promise(resolve => {});
}

/**
 * Create chat window manager, discuss, and messaging menu with
 * messaging store
 *
 * @param {Object} params
 * @param {boolean} [params.autoOpenDiscuss=false]
 * @param {boolean} [params.debug=false]
 * @param {Object} [params.initStoreStateAlteration]
 * @param {Object} [params.intercepts]
 * @param {Object} [params.session={}]
 * @param {string} [params.session.name="Admin"]
 * @param {integer} [params.session.partner_id=3]
 * @param {string} [params.session.partner_display_name="Your Company, Admin"]
 * @param {integer} [params.session.uid=2]
 * @return {Promise}
 */
async function start(params) {
    const Parent = Widget.extend({
        do_push_state: function () {},
    });
    const parent = new Parent();
    params.archs = params.archs || {
        'mail.message,false,search': '<search/>',
    };
    params.services = params.services || getMailServices();
    params.session = params.session || {};
    _.defaults(params.session, {
        name: "Admin",
        partner_id: 3,
        partner_display_name: "Your Company, Admin",
        uid: 2,
    });
    const selector = params.debug ? 'body' : '#qunit-fixture';
    params.services.env.prototype.TEST_ENV.active = true;
    let ORIGINAL_STORE_SERVICE_TEST_ENV = params.services.store.prototype.TEST_ENV;
    Object.assign(params.services.store.prototype.TEST_ENV, {
        active: true,
        initStateAlteration: params.initStoreStateAlteration || {
            globalWindow: {
                innerHeight: 1080,
                innerWidth: 1920,
            },
            isMobile: false,
        }
    });
    let ORIGINAL_CHAT_WINDOW_SERVICE_TEST_ENV = params.services.chat_window.prototype.TEST_ENV;
    Object.assign(params.services.chat_window.prototype.TEST_ENV, {
        active: true,
        container: selector,
    });
    testUtils.mock.addMockEnvironment(parent, params);
    const discuss = new Discuss(parent, params);
    const menu = new MessagingMenu(parent, params);
    const widget = new Widget(parent);

    Object.assign(widget, {
        closeDiscuss() {
            discuss.on_detach_callback();
        },
        destroy() {
            params.services.chat_window.prototype.TEST_ENV = ORIGINAL_CHAT_WINDOW_SERVICE_TEST_ENV;
            params.services.env.prototype.TEST_ENV.active = false;
            params.services.store.prototype.TEST_ENV = ORIGINAL_STORE_SERVICE_TEST_ENV;
            delete widget.destroy;
            delete window.o_test_store;
            widget.call('chat_window', 'destroy');
            parent.destroy();
        },
        openDiscuss() {
            discuss.on_attach_callback();
        },
    });

    await widget.appendTo($(selector));
    widget.call('chat_window', 'test:web_client_ready'); // trigger mounting of chat window manager
    await menu.appendTo($(selector));
    menu.on_attach_callback(); // trigger mounting of menu component
    await discuss.appendTo($(selector));
    if (params.autoOpenDiscuss) {
        widget.openDiscuss();
    }
    await testUtils.nextTick(); // mounting of chat window manager, discuss, and messaging menu
    const store = await widget.call('store', 'get');
    if (params.debug) {
        window.o_test_store = store;
    }
    return { discuss, store, widget };
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

return {
    afterEach,
    beforeEach,
    dragoverFiles,
    dropFiles,
    getMailServices,
    inputFiles,
    pasteFiles,
    pause,
    start,
};

});
