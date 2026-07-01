import { Component, onWillStart, signal, plugin, props, types as t } from "@odoo/owl";
import { DashboardPlugin } from "./dashboard_plugin";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

import { DashboardBlock } from "./components/dashboard_block";
import { DatabaseDialog } from "./components/database_dialog"

export class DatabaseSection extends Component {
    static template = "mysubscription.DatabaseSection";
    static components = { DashboardBlock, DatabaseDialog, Dropdown, DropdownItem };

    props = props({
        baseUrl: t.string(),
    });

    setup() {
        this.serverVersion = session.server_version;
        this.dashboardState = plugin(DashboardPlugin).state;
        this.dialog = useService("dialog");

        this.currentDbName = signal(session.db);

        onWillStart(async () => {
            this.databases = await rpc("/web/database/list");
            this.isSystem = await user.hasGroup("base.group_system");
        });
    }

    get databaseUrl() {
        return this.dashboardState.baseUrl;
    }

    get showDatabaseSelector() {
        return this.databases.length > 1;
    }

    downloadBackup() {
        this.dialog.add(DatabaseDialog, {
            action: "backup",
            dbName: this.currentDbName(),
        });
    }

    duplicateDatabase() {
        this.dialog.add(DatabaseDialog, {
            action: "duplicate",
            dbName: this.currentDbName(),
        });
    }

    dropDatabase() {
        this.dialog.add(DatabaseDialog, {
            action: "drop",
            dbName: this.currentDbName(),
        });
    }

    renameDatabase() {
        this.dialog.add(DatabaseDialog, {
            action: "rename",
            dbName: this.currentDbName(),
        })
    }

    get upgradeHref() {
        return this.dashboardState.hasSubscription
            ? "https://upgrade.odoo.com/#onpremise"
            : "https://www.odoo.com/pricing";
    }
}
