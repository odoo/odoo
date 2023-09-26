/* @odoo-module */

import { onChange } from "@mail/utils/common/misc";

import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { modelRegistry, preinsert, Record, RecordInverses, RecordList } from "./record";

export class Store extends Record {
    /** @returns {import("models").Store} */
    static insert() {
        return super.insert();
    }

    /** @type {typeof import("@mail/core/web/activity_model").Activity} */
    Activity;
    /** @type {typeof import("@mail/core/common/attachment_model").Attachment} */
    Attachment;
    /** @type {typeof import("@mail/core/common/canned_response_model").CannedResponse} */
    CannedResponse;
    /** @type {typeof import("@mail/core/common/channel_member_model").ChannelMember} */
    ChannelMember;
    /** @type {typeof import("@mail/core/common/chat_window_model").ChatWindow} */
    ChatWindow;
    /** @type {typeof import("@mail/core/common/composer_model").Composer} */
    Composer;
    /** @type {typeof import("@mail/core/common/discuss_app_model").DiscussApp} */
    DiscussApp;
    /** @type {typeof import("@mail/core/common/discuss_app_category_model").DiscussAppCategory} */
    DiscussAppCategory;
    /** @type {typeof import("@mail/core/common/follower_model").Follower} */
    Follower;
    /** @type {typeof import("@mail/core/common/link_preview_model").LinkPreview} */
    LinkPreview;
    /** @type {typeof import("@mail/core/common/message_model").Message} */
    Message;
    /** @type {typeof import("@mail/core/common/message_reactions_model").MessageReactions} */
    MessageReactions;
    /** @type {typeof import("@mail/core/common/notification_model").Notification} */
    Notification;
    /** @type {typeof import("@mail/core/common/notification_group_model").NotificationGroup} */
    NotificationGroup;
    /** @type {typeof import("@mail/core/common/persona_model").Persona} */
    Persona;
    /** @type {typeof import("@mail/discuss/call/common/rtc_session_model").RtcSession} */
    RtcSession;
    /** @type {typeof import("@mail/core/common/thread_model").Thread} */
    Thread;

    lastChannelSubscription = "";
    /** This is the current logged partner */
    user = Record.one("Persona");
    /** This is the current logged guest */
    guest = Record.one("Persona");
    /**
     * The last id of bus notification at the time for fetch init_messaging.
     * When receiving a notification:
     * - if id greater than this value: the notification is newer than init_messaging state.
     * - if same id or lower: the notification is older than init_messaging state.
     * This is useful to determine whether we should increment or decrement a counter based
     * on init_messaging state.
     */
    initBusId = 0;
    /**
     * Indicates whether the current user is using the application through the
     * public page.
     */
    inPublicPage = false;
    companyName = "";
    odoobot = Record.one("Persona");
    odoobotOnboarding;
    users = {};
    internalUserGroupId = null;
    registeredImStatusPartners = null;
    hasLinkPreviewFeature = true;
    // messaging menu
    menu = { counter: 0 };
    discuss = Record.one("DiscussApp");
    activityCounter = 0;
    isMessagingReady = false;

    get self() {
        return this.guest ?? this.user;
    }

    setup() {
        super.setup();
        this.updateBusSubscription = debounce(this.updateBusSubscription, 0); // Wait for thread fully inserted.
    }

    /**
     * @param {string} localId
     * @returns {Record}
     */
    get(localId) {
        if (typeof localId !== "string") {
            return undefined;
        }
        const modelName = Record.modelFromLocalId(localId);
        return this[modelName].records[localId];
    }

    updateBusSubscription() {
        const channelIds = [];
        const ids = Object.keys(this.Thread.records).sort(); // Ensure channels processed in same order.
        for (const id of ids) {
            const thread = this.Thread.records[id];
            if (thread.model === "discuss.channel" && thread.hasSelfAsMember) {
                channelIds.push(id);
            }
        }
        const channels = JSON.stringify(channelIds);
        if (this.isMessagingReady && this.lastChannelSubscription !== channels) {
            this.env.services["bus_service"].forceUpdateChannels();
        }
        this.lastChannelSubscription = channels;
    }
}
Store.register();

export const storeService = {
    dependencies: ["bus_service", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const res = {
            // fake store for now, until it becomes a model
            /** @type {Store} */
            store: {
                env,
                get: (...args) => Store.prototype.get.call(this, ...args),
            },
        };
        const Models = {};
        for (const [name, _OgClass] of modelRegistry.getEntries()) {
            /** @type {typeof Record} */
            const OgClass = _OgClass;
            if (res.store[name]) {
                throw new Error(
                    `There must be no duplicated Model Names (duplicate found: ${name})`
                );
            }
            // classes cannot be made reactive because they are functions and they are not supported.
            // work-around: make an object whose prototype is the class, so that static props become
            // instance props.
            const Model = Object.assign(Object.create(OgClass), { env, store: res.store });
            // Produce another class with changed prototype, so that there are automatic get/set on relational fields
            const Class = {
                [OgClass.name]: class extends OgClass {
                    constructor() {
                        super();
                        for (const name of Model.__rels__.keys()) {
                            // Relational fields contain symbols for detection in original class.
                            // This constructor is called on genuine records:
                            // - 'one' fields => undefined
                            // - 'many' fields => RecordList
                            let newVal;
                            if (this[name]?.[0] === Record.one()[0]) {
                                newVal = undefined;
                            }
                            if (this[name]?.[0] === Record.many()[0]) {
                                newVal = new RecordList();
                                newVal.__store__ = res.store;
                                newVal.name = name;
                                newVal.owner = this;
                            }
                            this.__rels__.set(name, newVal);
                            this.__invs__ = new RecordInverses();
                            this[name] = newVal;
                        }
                        return new Proxy(this, {
                            /** @param {Record} receiver */
                            get(target, name, receiver) {
                                if (name !== "__rels__" && receiver.__rels__.has(name)) {
                                    const l1 = receiver.__rels__.get(name);
                                    if (l1 instanceof RecordList) {
                                        return l1;
                                    }
                                    return res.store.get(l1);
                                }
                                return Reflect.get(target, name, receiver);
                            },
                            deleteProperty(target, name) {
                                if (name !== "__rels__" && target.__rels__.has(name)) {
                                    const r1 = target;
                                    const l1 = r1.__rels__.get(name);
                                    const r2 = res.store.get(l1);
                                    if (r2) {
                                        r2.__invs__.delete(r1.localId, name);
                                    }
                                    r1.__rels__.set(name, undefined);
                                }
                                const ret = Reflect.deleteProperty(target, name);
                                return ret;
                            },
                            /** @param {Record} receiver */
                            set(target, name, val, receiver) {
                                if (!receiver.__rels__.has(name)) {
                                    Reflect.set(target, name, val, receiver);
                                    return true;
                                }
                                const oldVal = receiver.__rels__.get(name);
                                if (oldVal instanceof RecordList) {
                                    // [Record.many] =
                                    const r1 = receiver;
                                    /** @type {RecordList<Record>} */
                                    const l1 = r1.__rels__.get(name);
                                    /** @type {Record[]|Set<Record>|RecordList<Record>} */
                                    const collection = val;
                                    const oldRecords = l1.slice();
                                    for (const r2 of oldRecords) {
                                        r2.__invs__.delete(r1.localId, name);
                                    }
                                    l1.clear();
                                    if ([null, false, undefined].includes(val)) {
                                        return true;
                                    }
                                    for (const v of collection) {
                                        preinsert(v, r1, name, (r3) => {
                                            l1.__list__.push(r3.localId);
                                            r3.__invs__.add(r1.localId, name);
                                        });
                                    }
                                } else {
                                    // [Record.one] =
                                    const r1 = receiver;
                                    const l1 = r1.__rels__.get(name);
                                    const r2 = res.store.get(l1);
                                    if (r2) {
                                        r2.__invs__.delete(r1.localId, name);
                                    }
                                    if ([null, false, undefined].includes(val)) {
                                        delete receiver[name];
                                        return true;
                                    }
                                    preinsert(val, r1, name, (r3) => {
                                        r1.__rels__.set(name, r3?.localId);
                                    });
                                }
                                return true;
                            },
                        });
                    }
                },
            }[OgClass.name];
            Object.assign(Model, {
                Class,
                records: JSON.parse(JSON.stringify(OgClass.records)),
                __rels__: new Map(),
            });
            Models[name] = Model;
            res.store[name] = Model;
            // Detect relational fields with a dummy record and setup getter/setters on them
            const obj = new OgClass();
            for (const [name, val] of Object.entries(obj)) {
                if (![Record.one()[0], Record.many()[0]].includes(val?.[0])) {
                    continue;
                }
                Model.__rels__.set(name, { targetModel: val[1] });
            }
        }
        // Make true store (as a model)
        res.store = reactive(res.store.Store.insert());
        res.store.env = env;
        for (const Model of Object.values(Models)) {
            Model.store = res.store;
            res.store[Model.name] = Model;
        }
        const store = res.store;
        store.discuss = {};
        store.discuss.activeTab = env.services.ui.isSmall ? "mailbox" : "all";
        onChange(store.Thread, "records", () => store.updateBusSubscription());
        services.ui.bus.addEventListener("resize", () => {
            if (!services.ui.isSmall) {
                store.discuss.activeTab = "all";
            } else {
                store.discuss.activeTab = store.discuss.thread?.type ?? "all";
            }
        });
        return store;
    },
};

registry.category("services").add("mail.store", storeService);
