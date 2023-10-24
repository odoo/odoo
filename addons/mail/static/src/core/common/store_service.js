/* @odoo-module */

import { onChange } from "@mail/utils/common/misc";

import { markup, reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { modelRegistry, Record, RecordUses, RecordList } from "./record";

/**
 * Class of markup, useful to detect content that is markup and to
 * automatically markup field during trusted insert
 */
const Markup = markup("").constructor;

export class BaseStore extends Record {
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
}

export class Store extends BaseStore {
    /** @returns {import("models").Store|import("models").Store[]} */
    static insert() {
        return super.insert(...arguments);
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
    /** @type {typeof import("@mail/core/common/failure_model").Failure} */
    Failure;
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
    failures = Record.many("Failure");
    activityCounter = 0;
    isMessagingReady = false;

    get self() {
        return this.guest ?? this.user;
    }

    setup() {
        super.setup();
        this.updateBusSubscription = debounce(this.updateBusSubscription, 0); // Wait for thread fully inserted.
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

export function makeStore(env) {
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
            throw new Error(`There must be no duplicated Model Names (duplicate found: ${name})`);
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
                    const proxy = new Proxy(this, {
                        /** @param {Record} receiver */
                        get(target, name, receiver) {
                            if (name !== "_fields" && name in receiver._fields) {
                                const l1 = receiver._fields[name];
                                if (RecordList.isMany(l1)) {
                                    return l1;
                                }
                                return l1[0];
                            }
                            return Reflect.get(target, name, receiver);
                        },
                        deleteProperty(target, name) {
                            if (name !== "_fields" && name in target._fields) {
                                const r1 = target;
                                const l1 = r1._fields[name];
                                l1.clear();
                                return true;
                            }
                            const ret = Reflect.deleteProperty(target, name);
                            return ret;
                        },
                        /** @param {Record} receiver */
                        set(target, name, val, receiver) {
                            if (name === "Model" || !(name in receiver.Model._fields)) {
                                Reflect.set(target, name, val, receiver);
                                return true;
                            }
                            if (Record.isAttr(receiver.Model._fields[name])) {
                                if (
                                    receiver.Model._fields[name].html &&
                                    Record.trusted &&
                                    typeof val === "string" &&
                                    !(val instanceof Markup)
                                ) {
                                    Reflect.set(target, name, markup(val), receiver);
                                } else {
                                    Reflect.set(target, name, val, receiver);
                                }
                                return true;
                            }
                            /** @type {RecordList<Record>} */
                            const l1 = receiver._fields[name];
                            if (RecordList.isMany(l1)) {
                                // [Record.many] =
                                if (Record.isCommand(val)) {
                                    for (const [cmd, cmdData] of val) {
                                        if (Array.isArray(cmdData)) {
                                            for (const item of cmdData) {
                                                if (cmd === "ADD") {
                                                    l1.add(item);
                                                } else if (cmd === "ADD.noinv") {
                                                    l1._addNoinv(item);
                                                } else if (cmd === "DELETE.noinv") {
                                                    l1._deleteNoinv(item);
                                                } else {
                                                    l1.delete(item);
                                                }
                                            }
                                        } else {
                                            if (cmd === "ADD") {
                                                l1.add(cmdData);
                                            } else if (cmd === "ADD.noinv") {
                                                l1._addNoinv(cmdData);
                                            } else if (cmd === "DELETE.noinv") {
                                                l1._deleteNoinv(cmdData);
                                            } else {
                                                l1.delete(cmdData);
                                            }
                                        }
                                    }
                                    return true;
                                }
                                if ([null, false, undefined].includes(val)) {
                                    l1.clear();
                                    return true;
                                }
                                if (!Array.isArray(val)) {
                                    val = [val];
                                }
                                /** @type {Record[]|Set<Record>|RecordList<Record>} */
                                const collection = Record.isRecord(val) ? [val] : val;
                                const oldRecords = l1.slice();
                                for (const r2 of oldRecords) {
                                    r2.__uses__.delete(l1);
                                }
                                // l1 and collection could be same record list,
                                // save before clear to not push mutated recordlist that is empty
                                const col = [...collection];
                                l1.clear();
                                l1.push(...col);
                            } else {
                                // [Record.one] =
                                if (Record.isCommand(val)) {
                                    const [cmd, cmdData] = val.at(-1);
                                    if (cmd === "ADD") {
                                        l1.add(cmdData);
                                    } else if (cmd === "ADD.noinv") {
                                        l1._addNoinv(cmdData);
                                    } else if (cmd === "DELETE.noinv") {
                                        l1._deleteNoinv(cmdData);
                                    } else {
                                        l1.delete(cmdData);
                                    }
                                    return true;
                                }
                                if ([null, false, undefined].includes(val)) {
                                    delete receiver[name];
                                    return true;
                                }
                                l1.add(val);
                            }
                            return true;
                        },
                    });
                    if (this instanceof BaseStore) {
                        res.store = proxy;
                    }
                    for (const name in Model._fields) {
                        if (Record.isRelation(this[name]?.[0])) {
                            // Relational fields contain symbols for detection in original class.
                            // This constructor is called on genuine records:
                            // - 'one' fields => undefined
                            // - 'many' fields => RecordList
                            // this[name]?.[0] is ONE_SYM or MANY_SYM
                            const newVal = new RecordList(this[name]?.[0]);
                            if (this instanceof BaseStore) {
                                newVal.store = proxy;
                            } else {
                                newVal.store = res.store;
                            }
                            newVal.name = name;
                            newVal.owner = proxy;
                            this._fields[name] = newVal;
                            this.__uses__ = new RecordUses();
                            this[name] = newVal;
                        } else {
                            this[name] = Model._fields[name].default;
                        }
                    }
                    for (const [name, fn] of Object.entries(Model.__computes__)) {
                        let boundFn;
                        const proxy2 = reactive(proxy, () => boundFn());
                        boundFn = () => (proxy[name] = fn.call(proxy2));
                        this.__computes__[name] = boundFn;
                    }
                    return proxy;
                }
            },
        }[OgClass.name];
        Object.assign(Model, {
            Class,
            records: JSON.parse(JSON.stringify(OgClass.records)),
            _fields: {},
            __computes__: {},
        });
        Models[name] = Model;
        res.store[name] = Model;
        // Detect fields with a dummy record and setup getter/setters on them
        const obj = new OgClass();
        for (const [name, val] of Object.entries(obj)) {
            const SYM = val?.[0];
            if (!Record.isField(SYM)) {
                continue;
            }
            Model._fields[name] = { [SYM]: true, ...val[1] };
            if (val[1].compute) {
                Model.__computes__[name] = val[1].compute;
            }
        }
    }
    // Sync inverse fields
    for (const Model of Object.values(Models)) {
        for (const [name, definition] of Object.entries(Model._fields)) {
            if (!Record.isRelation(definition)) {
                continue;
            }
            const { targetModel, inverse } = definition;
            if (targetModel && !Models[targetModel]) {
                throw new Error(`No target model ${targetModel} exists`);
            }
            if (inverse) {
                const rel2 = Models[targetModel]._fields[inverse];
                if (rel2.targetModel && rel2.targetModel !== Model.name) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong targetModel. Expected: "${Model.name}" Actual: "${rel2.targetModel}"`
                    );
                }
                if (rel2.inverse && rel2.inverse !== name) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong inverse. Expected: "${name}" Actual: "${rel2.inverse}"`
                    );
                }
                Object.assign(rel2, { targetModel: Model.name, inverse: name });
            }
        }
    }
    // Make true store (as a model)
    res.store = reactive(res.store.Store.insert());
    res.store.env = env;
    for (const Model of Object.values(Models)) {
        Model.store = res.store;
        res.store[Model.name] = Model;
    }
    return res.store;
}

export const storeService = {
    dependencies: ["bus_service", "ui"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const store = makeStore(env);
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
