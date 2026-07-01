import { Component, signal, props, types as t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class DatabaseDialog extends Component {
    static components = { Dialog };
    static template = "mysubscription.DatabaseDialog";
    props = props({
        action: t.string(),
        dbName: t.string(),
        close: t.function(),
    });

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        const timestamp = DateTime.now().toFormat("yyyy-MM-dd_HH-mm-ss");

        this.isProcessing = signal(false);
        this.masterPwd = signal("");
        this.duplicateName = signal("");
        this.duplicateNeutralize = signal(true);
        this.backupFilename = signal(`${this.props.dbName}_${timestamp}`);
        this.backupFormat = signal("zip");
    }

    get title() {
        const titles = {
            backup: "Backup",
            duplicate: "Duplicate",
            rename: "Rename",
            drop: "Delete",
        }
        return `${titles[this.props.action]} ${this.props.dbName}`;
    }

    get formData() {
        /*
        - backup HTTP:    master_pwd, name, backup_format='zip', filestore=True
        - duplicate HTTP: master_pwd, name, new_name, neutralize_database=False
        - drop HTTP:      master_pwd, name
        - rename HTTP:    master_pwd, name, new_name --> (duplicate + drop)
        */
        const formData = new FormData();

        formData.append("master_pwd", this.masterPwd());
        formData.append("name", this.props.dbName);

        switch (this.props.action) {
            case "backup":
                formData.append("backup_format", this.backupFormat());
                formData.append("filestore", true);
                break;
            case "duplicate":
                formData.append("new_name", this.duplicateName());
                formData.append("neutralize_database", this.duplicateNeutralize());
                break;
            case "rename":
                formData.append("new_name", this.duplicateName());
                formData.append("neutralize_database", false);
        }
        return formData;
    }

    async onBackupBeforeDrop() {
        this.dialog.add(DatabaseDialog, {
            action: "backup",
            dbName: this.props.dbName,
        })
    }

    async _onSubmitBackup(response) {
        const backupFileName = `${this.backupFilename()}.${this.backupFormat()}`;

        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = backupFileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    }

    async _executeAction(action) {
        const formData = this.formData;
        try {
            const route = `/web/database/${action}`;
            const response = await fetch(route, {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                this.notification.add(`Action failed. Check password.`, { type: "danger" });
                this.isProcessing.set(false);
                if (action === "drop" && response.status === 500) {
                    location.reload();
                }
                return;
            }
            switch (action) {
                case "backup":
                    await this._onSubmitBackup(response);
                    break;
                case "duplicate":
                    break;
                case "rename":
                case "drop":
                    // Reloading leads the user to the database manager.
                    location.reload();
                    break;
            }
            this.props.close();
            this.notification.add(_t("Action completed successfully!"), { type: "success" });

        } catch (error) {
            console.error(error);
            this.notification.add(_t("A network error occurred."), { type: "danger" });
            this.isProcessing.set(false);
        }
    }

    async onSubmit() {
        this.isProcessing.set(true);
        await this._executeAction(this.props.action);
    }

    get confirmButtonText() {
        if (this.isProcessing()) {
            return "Processing...";
        } else {
            switch (this.props.action) {
                case "backup":
                    return "Backup";
                case "duplicate":
                    return "Duplicate";
                case "rename":
                    return "Rename";
                case "drop":
                    return "Delete";
            }
        }
    }
}
