export default class DeviceIdentifierSequence {
    static uniqueDeviceIdentifierKey = `${odoo.access_token}-unique_device_identifier`;

    constructor({ orm }) {
        this.orm = orm;
        this.device_identifier = "";
    }

    get data() {
        const localStorageKey = DeviceIdentifierSequence.uniqueDeviceIdentifierKey;
        return JSON.parse(localStorage.getItem(localStorageKey));
    }

    get identifier() {
        const data = this.data;
        return data.device_identifier;
    }

    get unsyncedNumberStack() {
        const data = this.data;
        return data.unsynced_number_stack || [];
    }

    get nextNumber() {
        const data = this.data;
        return data.unsynced_number_stack.length
            ? data.unsynced_number_stack.sort((a, b) => a - b)[0]
            : data.next_number;
    }

    async initialize() {
        const localStorageKey = DeviceIdentifierSequence.uniqueDeviceIdentifierKey;
        const deviceIdentifier = localStorage.getItem(localStorageKey);

        if (!deviceIdentifier) {
            const data = await this.orm.call("pos.config", "register_new_device_identifier", [
                odoo.pos_config_id,
            ]);

            this.device_identifier = data.device_identifier;
            this.save({
                device_identifier: data.device_identifier,
                next_number: 1,
                unsynced_number_stack: [],
            });
        }
    }

    getFirstUnsyncedNumber() {
        const unsyncedNumberStack = this.unsyncedNumberStack;
        const sorted = unsyncedNumberStack.sort((a, b) => a - b);
        if (sorted.length === 0) {
            return null;
        }

        this.save({
            device_identifier: this.data.device_identifier,
            next_number: this.data.next_number,
            unsynced_number_stack: sorted.slice(1), // Remove the first element from the stack
        });

        return sorted[0];
    }

    useNext() {
        const unsyncedNumber = this.getFirstUnsyncedNumber();
        if (unsyncedNumber) {
            return unsyncedNumber;
        }

        const data = this.data;
        const number = data.next_number;
        const newData = {
            device_identifier: data.device_identifier,
            next_number: number + 1,
            unsynced_number_stack: [], // In case of order deletion, its identifier will be added to this stack to be reused later
        };

        this.save(newData);
        return number;
    }

    save({ next_number, device_identifier, unsynced_number_stack }) {
        const localStorageKey = DeviceIdentifierSequence.uniqueDeviceIdentifierKey;
        const current = this.data;
        const data = {
            device_identifier: device_identifier || current.device_identifier,
            next_number: next_number || current.next_number,
            unsynced_number_stack: [
                ...new Set(unsynced_number_stack || current.unsynced_number_stack || []),
            ],
        };
        localStorage.setItem(localStorageKey, JSON.stringify(data));
    }

    saveUnusedNumber(orders) {
        const data = this.data;
        if (!data) {
            return;
        }
        const numbers = orders
            .filter((o) => !o.isSynced)
            .map((o) => this.extractNumberFromReference(o.pos_reference));
        const unsyncedNumberStack = new Set([...data.unsynced_number_stack, ...numbers]);

        this.save({
            device_identifier: data.device_identifier,
            next_number: data.next_number,
            unsynced_number_stack: Array.from(unsyncedNumberStack),
        });
    }

    extractNumberFromReference(reference) {
        return parseInt(reference.split("-")[2]);
    }
}
