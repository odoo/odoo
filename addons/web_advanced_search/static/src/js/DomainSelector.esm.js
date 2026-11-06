/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {_t} from "web.core";
import Domain from "web.Domain";
import DomainSelector from "web.DomainSelector";
import basic_fields from "web.basic_fields";
/**
 * The redraw in the Debug Field does not trigger correctly
 * so we overwrite it with the v14 Version
 *
 */
patch(DomainSelector.prototype, "web.DomainSelector", {
    /**
     * @override
     */
    _onDebugInputChange(e) {
        if (!$(".o_add_advanced_search").length) {
            return this._super(...arguments);
        }
        const rawDomain = e.currentTarget.value;
        try {
            Domain.prototype.stringToArray(rawDomain);
        } catch (err) {
            // If there is a syntax error, just ignore the change
            this.displayNotification({
                title: _t("Syntax error"),
                message: _t("Domain not properly formed"),
                type: "danger",
            });
            return;
        }
        this._redraw(Domain.prototype.stringToArray(rawDomain)).then(
            function () {
                this.trigger_up("domain_changed", {
                    child: this,
                    alreadyRedrawn: true,
                });
            }.bind(this)
        );
    },
});

patch(basic_fields.FieldDomain.prototype, "web.basic_fields", {
    /**
     * Odoo restricts re-rendering the domain from the debug editor for supposedly
     * performance reasons. We didn't ever came up with those and in v17 it's supported
     * in the new advanced search.
     * @override
     */
    // eslint-disable-next-line
    _onDomainSelectorValueChange(event) {
        this._super(...arguments);
        // Deactivate all debug conditions that cripple the functionality
        this.debugEdition = false;
    },
});
