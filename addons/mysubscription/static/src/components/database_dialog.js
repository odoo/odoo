import { Component, computed, signal, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class DatabaseDialog extends Component {
    static components = { Dialog };
    static template = "mysubscription.DatabaseDialog";
    props = useProps({
        action: t.string(),
        dbName: t.string(),
        close: t.function(),
    });

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.http = useService("http");

        const timestamp = DateTime.now().toFormat("yyyy-MM-dd_HH-mm-ss");

        this.isProcessing = signal(false);
        this.masterPwd = signal("");
        this.duplicateName = signal("");
        this.duplicateNeutralize = signal(true);
        this.backupFilename = signal(`${this.props.dbName}_${timestamp}`);
        this.backupFormat = signal("zip");
    }

    title = computed(() => {
        const titles = {
            backup: "Backup",
            duplicate: "Duplicate",
            rename: "Rename",
            drop: "Delete",
        }
        return `${titles[this.props.action]} ${this.props.dbName}`;
    });

    formData() {
        /*
        - backup HTTP:    master_pwd, name, backup_format='zip', filestore=True
        - duplicate HTTP: master_pwd, name, new_name, neutralize_database=False
        - drop HTTP:      master_pwd, name
        - rename HTTP:    master_pwd, name, new_name
        */
        const formData = {
            master_pwd: this.masterPwd(),
            name: this.props.dbName,
        };

        switch (this.props.action) {
            case "backup":
                formData.backup_format = this.backupFormat();
                formData.filestore = true;
                break;
            case "duplicate":
                formData.new_name = this.duplicateName();
                formData.neutralize_database = this.duplicateNeutralize();
                break;
            case "rename":
                formData.new_name = this.duplicateName();
                break;
        }
        return formData;
    }

    async onBackupBeforeDrop() {
        this.dialog.add(DatabaseDialog, {
            action: "backup",
            dbName: this.props.dbName,
        })
    }

    async _onSubmitBackup(blob) {
        const backupFileName = `${this.backupFilename()}.${this.backupFormat()}`;
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
        const params = this.formData();
        const route = `/web/database/${action}`;

        if (action === "backup") {
            const response = await this.http.post(route, params, "response");
            if (!response.ok) {
                this.notification.add(_t("Action failed. Invalid or missing master password."), { type: "danger" });
                return;
            }
            await this._onSubmitBackup(await response.blob());
        } else {
            const finalUrl = await this.http.post(route, params, "url");
            if (!finalUrl.endsWith("/web/database/manager")) {
                this.notification.add(_t("Action failed. Invalid or missing master password."), { type: "danger" });
                return;
            }
            location.reload();
        }

        this.props.close();
        this.notification.add(_t("Action completed successfully!"), { type: "success" });
    }

    async onSubmit() {
        this.isProcessing.set(true)
        try {
            await this._executeAction(this.props.action)
        } catch {
            this.notification.add(_t("A network error occurred."), { type: "danger" });
        } finally {
            this.isProcessing.set(false)
        }
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
