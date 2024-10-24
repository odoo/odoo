import { onPatched, onWillUnmount, onMounted } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/*
The PopoutableMixin is a component which can popout an external window (with another component and props in the popout window).
The PopoutableMixin definition assumes that only one PopoutableMixin can exist in a single UI page (to control a single popout window).
This is because the mixin overrides the content of the popout window onces it's mounted or patched.
Multiple PopoutableMixins can coexist in a single UI page if they would popout the same component with the same props (e.g., Chatter and AttachmentView).
*/
export const PopoutableMixin = (component) =>
    class extends component {
        setup() {
            super.setup();
            this.mailPopoutService = useService("mail.popout");

            onMounted(this.updatePopout);
            onPatched(this.updatePopout);
            onWillUnmount(this.resetPopout);
        }

        /********** To be overridden **********/
        beforePopout() {}
        afterPopoutClosed() {}
        get popoutComponent() {
            return component;
        }
        get popoutProbs() {
            return this.props;
        }
        /************************************/

        popout() {
            this.mailPopoutService.addHooks(
                this.beforePopout.bind(this),
                this.afterPopoutClosed.bind(this)
            );
            this.mailPopoutService.popout(this.popoutComponent, this.popoutProbs);
        }

        updatePopout() {
            if (this.mailPopoutService.externalWindow) {
                this.popout();
            }
        }

        resetPopout() {
            this.mailPopoutService.reset();
        }
    };
