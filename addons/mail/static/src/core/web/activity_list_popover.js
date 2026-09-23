// @ts-check
/** @odoo-module native */
import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { compareDatetime } from "@mail/utils/common/misc";
import { Component, onWillUpdateProps } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useService } from "@web/core/utils/hooks";

const log = makeLogger("mail.activity");
/**
 * @typedef {Object} Props
 * @property {number[]} activityIds
 * @property {function} close
 * @property {number} [defaultActivityTypeId]
 * @property {function} onActivityChanged
 * @property {number[]} [resIds]
 * @property {number} resId
 * @property {string} resModel
 * @extends {Component<Props, import("@web/env").OdooEnv>}
 */
export class ActivityListPopover extends Component {
    static components = { ActivityListPopoverItem };
    static props = [
        "activityIds",
        "close",
        "defaultActivityTypeId?",
        "onActivityChanged",
        "resId",
        "resIds?",
        "resModel",
    ];
    static template = "mail.ActivityListPopover";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.updateFromProps(this.props).catch(() => {});
        onWillUpdateProps(
            /** @param {{activityIds: number[]}} props */ (props) =>
                this.updateFromProps(props).catch(() => {}),
        );
    }

    computeActivityBuckets() {
        /** @type {import("models").Activity[]} */
        const activities = this.props.activityIds
            .map((id) => this.store["mail.activity"].get(id))
            .filter(Boolean)
            .sort(
                (a, b) =>
                    compareDatetime(a.date_deadline, b.date_deadline) || a.id - b.id,
            );
        /** @type {Record<string, import("models").Activity[]>} */
        const buckets = { done: [], overdue: [], planned: [], today: [] };
        for (const activity of activities) {
            buckets[activity.state]?.push(activity);
        }
        return { activities, ...buckets };
    }

    onClickAddActivityButton() {
        this.store
            .scheduleActivity(
                this.props.resModel,
                this.props.resIds ? this.props.resIds : [this.props.resId],
                this.props.defaultActivityTypeId,
            )
            .then(() => this.props.onActivityChanged());
        this.props.close();
    }

    /** @param {{activityIds: number[]}} props */
    async updateFromProps(props) {
        const endFormat = log.perf("activity_format");
        const data = await this.orm.silent.call("mail.activity", "activity_format", [
            props.activityIds,
        ]);
        endFormat({ activities: props.activityIds.length });
        this.store.insert(data);
    }
}
