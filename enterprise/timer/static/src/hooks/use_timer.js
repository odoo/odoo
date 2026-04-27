import { onWillStart, useComponent } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export function useTimer() {
    const component = useComponent();
    const timerService = useService("timer");
    const timerReactive = timerService.createTimer();
    onWillStart(timerService.getServerOffset.bind(component));

    return timerReactive;
}
