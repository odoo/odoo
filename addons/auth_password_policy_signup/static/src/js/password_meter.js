/** @odoo-module */

import Widget from "@web/legacy/js/core/widget";
import { computeScore } from "@auth_password_policy/password_policy";
import { translationIsReady, _t } from "@web/core/l10n/translation";

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
    willStart() {
        return translationIsReady
    },
    start() {
        var helpMessage = _t(
            "Required: %s.\n\nHint: increase length, use multiple words and use non-letter characters to increase your password's strength.",
            String(this._required) || _t("no requirements")
        );
        this.el.setAttribute("title", helpMessage);
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
