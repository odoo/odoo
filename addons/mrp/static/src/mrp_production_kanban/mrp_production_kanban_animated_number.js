import { formatFloatTime } from '@web/views/fields/formatters';
import { AnimatedNumber } from "@web/views/view_components/animated_number";

export class MrpProductionAnimatedNumber extends AnimatedNumber {
    setup() {
        super.setup();
        this.constructor.enableAnimations = false;
    }
    format(value) {
        return formatFloatTime(Math.round(value), { unit: 'minutes' });
    }
}
