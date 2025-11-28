/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ModelFieldsCountListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            refresh_time: "",
            duration: 2,
            loading: false,
            isForceMode: false,
        });
        
        onWillStart(async () => {
            await this.loadVersion();
            if (this.state.web_auto_refresh && (
                !this.state.refresh_time ||
                new Date(this.state.refresh_time) < new Date(Date.now() - this.state.stale_threshold)
            )) {
                // automatically refresh if the view is stale after refresh the page
                await this.refresh_stale();
            }
        });
    }

    async loadVersion() {
        try {
            const {refresh_time, duration, stale_threshold, web_auto_refresh} = await this.orm.call(
                "model.fields.count",
                "freshness",
                []
            );
            if (refresh_time) {
                const date = new Date(refresh_time);
                this.state.refresh_time = date.toLocaleString();
                this.state.duration = duration;
                this.state.stale_threshold = stale_threshold;
                this.state.web_auto_refresh = web_auto_refresh;
            } else {
                this.state.refresh_time = undefined;
                this.state.duration = 3600;
                this.state.stale_threshold = 3600;
                this.state.web_auto_refresh = false;
            }
        } catch (error) {
            console.error("Error loading version:", error);
            this.state.refresh_time = "N/A";
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async onRefreshClick() {
        await this.refresh_stale();
    }

    async onForceRefreshClick() {
        await this.refresh_stale(0);
    }

    async refresh_stale(threshold) {
        if (this.state.loading) {
            return;
        }

        this.state.isForceMode = false;
        this.state.loading = true;
        const maxRetryTimes = 5; // Maximum retry times: 5
        let retryCount = 0;

        try {
            let success = false;
            let lastError = null;

            // Loop with retry mechanism based on count
            while (retryCount < maxRetryTimes) {
                try {
                    await this.orm.call(
                        "model.fields.count",
                        "refresh_stale",
                        [threshold] // Pass timeout parameter
                    );
                    
                    success = true;
                    break; // Exit loop on success
                } catch (error) {
                    lastError = error;
                    if (!error.message.includes("LockError")) {
                        break;
                    }
                    // retry from the webclient to avoid occupying the worker for retrying
                    retryCount++;
                    console.log(`Refresh error (attempt ${retryCount}/${maxRetryTimes}), retrying...`, error);

                    // Only sleep if we haven't reached max retries yet
                    if (retryCount < maxRetryTimes) {
                        const retryDelay = this.state.duration / 2;
                        await this.sleep(retryDelay);
                    }
                }
            }

            if (success) {                
                // Reload version and list
                await this.loadVersion();
                await this.model.load();
                this.model.notify();
            } else {
                throw lastError || new Error(`Refresh failed after ${maxRetryTimes} retries: ${lastError?.message}`);
            }
        } catch (error) {
            console.error("Error refreshing:", error);
            this.notification.add("Error refreshing materialized view: " + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }
}
    

export const modelFieldsCountListView = {
    ...listView,
    Controller: ModelFieldsCountListController,
    buttonTemplate: "model_fields_report.ListView.Buttons",
};

registry.category("views").add("model_fields_count_list", modelFieldsCountListView);

