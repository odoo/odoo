import { useRef } from "@web/owl2/utils";
import { Component, onMounted, props, t } from "@odoo/owl";

const AUTOCLOSE_DELAY = 4000;

export class Notification extends Component {
    static template = "web.NotificationWowl";
    props = props({
        message: t.customValidator(
            t.any(),
            (m) =>
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
        ),
        type: t.selection(["warning", "danger", "success", "info"]).optional("warning"),
        title: t.or([t.string(), t.boolean(), t.object({ toString: t.function() })]).optional(),
        className: t.string().optional(""),
        buttons: t
            .array(
                t.object({
                    name: t.string(),
                    icon: t.string().optional(),
                    primary: t.boolean().optional(),
                    onClick: t.function(),
                })
            )
            .optional([]),
        sticky: t.boolean().optional(),
        autocloseDelay: t.number().optional(AUTOCLOSE_DELAY),
        close: t.function(),
    });
    setup() {
        this.autocloseProgress = useRef("autoclose_progress_bar");
        onMounted(() => this.startNotificationTimer());
    }

    freeze() {
        this.startedTimestamp = false;
        this.autocloseProgress.el.style.width = 0;
    }

    refresh() {
        this.startNotificationTimer();
    }

    close() {
        this.props.close();
    }

    startNotificationTimer() {
        if (this.props.sticky) {
            return;
        }
        this.startedTimestamp = luxon.DateTime.now().ts;

        const cb = () => {
            if (this.startedTimestamp) {
                const currentProgress =
                    (luxon.DateTime.now().ts - this.startedTimestamp) / this.props.autocloseDelay;
                if (currentProgress > 1) {
                    this.close();
                    return;
                }
                if (this.autocloseProgress.el) {
                    this.autocloseProgress.el.style.width = `${(1 - currentProgress) * 100}%`;
                }
                requestAnimationFrame(cb);
            }
        };
        cb();
    }
}
