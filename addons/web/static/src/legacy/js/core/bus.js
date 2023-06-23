/** @odoo-module **/

import Class from "@web/legacy/js/core/class";
import mixins from "@web/legacy/js/core/mixins";

/**
 * Event Bus used to bind events scoped in the current instance
 *
 * @class Bus
 */
export default Class.extend(mixins.EventDispatcherMixin, {
    init: function (parent) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);
    },
});
