/** @odoo-module */

import { _t } from "web.core";
import Widget from "web.Widget";
import { computeScore } from "@auth_password_policy/password_policy";

export default Widget.extend({
    tagName: "meter",
    className: "o_password_meter",
    attributes: {
        min: 0,
        low: 0.5,
        high: 0.99,
        max: 1,
        length: 0,
        value: 0,
        optimum: 1,
    },
    init(parent, required, recommended) {
        this._super(parent);
        this._required = required;
        this._recommended = recommended;
    },
    start() {
        var helpMessage = _t(
            "Required: %s.\n\nHint: increase length, use multiple words and use non-letter characters to increase your password's strength."
        );
        this.el.setAttribute(
            "title",
            _.str.sprintf(helpMessage, String(this._required) || _t("no requirements"))
        );
        return this._super().then(function () {});
    },
    /**
     * Updates the meter with the information of the new password: computes
     * the (required x recommended) score and sets the widget's value as that
     *
     * @param {String} password
     */
    update(password) {
        this.el.setAttribute("length", password.length);
        this.el.value = computeScore(password, this._required, this._recommended);
    },
});
