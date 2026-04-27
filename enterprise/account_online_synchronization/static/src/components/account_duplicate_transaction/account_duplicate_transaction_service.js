import { registry } from "@web/core/registry";

class AccountDuplicateTransactionsServiceModel {
    constructor() {
        this.selectedLines = new Set();
    }

    updateLIne(selected, id) {
        this.selectedLines[selected ? "add" : "delete"](id);
    }
}

const duplicateCheckService = {
    start(env, services) {
        return new AccountDuplicateTransactionsServiceModel();
    },
};

registry
    .category("services")
    .add("account_online_synchronization.duplicate_check_service", duplicateCheckService);
