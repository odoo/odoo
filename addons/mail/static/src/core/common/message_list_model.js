import { AND, Record } from "@mail/core/common/record";
const FETCH_LIMIT = 30;

export class MessageList extends Record {
    static id = AND("thread", "source");

    source = Record.attr();
    messages = Record.many("Message");
    thread = Record.one("Thread");
    newestMessage = Record.many("Message", {
        compute() {
            return [...this.messages].reverse().find((msg) => !msg.isEmpty);
        },
    });
    newestPersistentMessage = Record.one("Message", {
        compute() {
            return [...this.messages].reverse().find((msg) => Number.isInteger(msg.id));
        },
    });
    oldestPersistentMessage = Record.one("Message", {
        compute() {
            return this.messages.find((msg) => Number.isInteger(msg.id));
        },
    });
    isEmpty = Record.attr(false, {
        compute() {
            return !this.messages.some((message) => !message.isEmpty);
        },
    });
    nonEmptyMessages = Record.many("Message", {
        compute() {
            return this.messages.filter((message) => !message.isEmpty);
        },
    });
    persistentMessages = Record.many("Message", {
        compute() {
            return this.messages.filter((message) => !message.is_transient);
        },
    });

    /**
     * @param {import("models").Thread} thread
     */
    async fetchNewMessages() {
        if (
            this.thread.status === "loading" ||
            (this.thread.isLoaded && ["discuss.channel", "mail.box"].includes(this.thread.model))
        ) {
            return;
        }
        const after = this.thread.isLoaded ? this.newestPersistentMessage?.id : undefined;
        try {
            const fetched = await this._store.env.services["mail.thread"].fetchMessages(
                this.thread,
                { after }
            );
            // feed messages
            // could have received a new message as notification during fetch
            // filter out already fetched (e.g. received as notification in the meantime)
            let startIndex;
            if (after === undefined) {
                startIndex = 0;
            } else {
                const afterIndex = this.messages.findIndex((message) => message.id === after);
                if (afterIndex === -1) {
                    // there might have been a jump to message during RPC fetch.
                    // Abort feeding messages as to not put holes in message list.
                    return;
                } else {
                    startIndex = afterIndex + 1;
                }
            }
            const alreadyKnownMessages = new Set(this.messages.map((m) => m.id));
            const filtered = fetched.filter(
                (message) =>
                    !alreadyKnownMessages.has(message.id) &&
                    (this.persistentMessages.length === 0 ||
                        message.id < this.oldestPersistentMessage.id ||
                        message.id > this.newestPersistentMessage.id)
            );
            this.messages.splice(startIndex, 0, ...filtered);
            Object.assign(this.thread, {
                loadOlder:
                    after === undefined && fetched.length === FETCH_LIMIT
                        ? true
                        : after === undefined && fetched.length !== FETCH_LIMIT
                        ? false
                        : this.thread.loadOlder,
            });
        } catch {
            // handled in fetchMessages
        }
    }

    /**
     * @param {import("models").Thread} thread
     * @param {"older"|"newer"} epoch
     */
    async fetchMoreMessages(epoch = "older") {
        if (
            this.thread.status === "loading" ||
            (epoch === "older" && !this.thread.loadOlder) ||
            (epoch === "newer" && !this.thread.loadNewer)
        ) {
            return;
        }
        const before = epoch === "older" ? this.oldestPersistentMessage?.id : undefined;
        const after = epoch === "newer" ? this.newestPersistentMessage?.id : undefined;
        try {
            const fetched = await this._store.env.services["mail.thread"].fetchMessages(
                this.thread,
                { after, before }
            );
            if (
                (after !== undefined && !this.messages.some((message) => message.id === after)) ||
                (before !== undefined && !this.messages.some((message) => message.id === before))
            ) {
                // there might have been a jump to message during RPC fetch.
                // Abort feeding messages as to not put holes in message list.
                return;
            }
            const alreadyKnownMessages = new Set(this.messages.map(({ id }) => id));
            const messagesToAdd = fetched.filter(
                (message) => !alreadyKnownMessages.has(message.id)
            );
            if (epoch === "older") {
                this.messages.unshift(...messagesToAdd);
            } else {
                this.messages.push(...messagesToAdd);
            }
            if (fetched.length < FETCH_LIMIT) {
                if (epoch === "older") {
                    this.thread.loadOlder = false;
                } else if (epoch === "newer") {
                    this.thread.loadNewer = false;
                    const missingMessages = this.thread.pendingNewMessages.filter(
                        ({ id }) => !alreadyKnownMessages.has(id)
                    );
                    if (missingMessages.length > 0) {
                        this.messages.push(...missingMessages);
                        this.messages.sort((m1, m2) => m1.id - m2.id);
                    }
                }
            }
            this._enrichMessagesWithTransient(this.thread);
        } catch {
            // handled in fetchMessages
        }
        this.thread.pendingNewMessages = [];
    }
}

MessageList.register();
