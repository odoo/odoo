/** @odoo-module alias=web.Bus **/

import Class from "web.Class";
import mixins from "web.mixins";

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
