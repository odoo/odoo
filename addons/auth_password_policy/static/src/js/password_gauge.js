odoo.define('auth_password_policy', function (require) {
"use strict";
var core = require('web.core');
var _t = core._t;

var Policy = core.Class.extend({
    /**
     *
     * @param {Object} info
     * @param {Number} [info.minlength=0]
     * @param {Number} [info.minwords=0]
     * @param {Number} [info.minclasses=0]
     */
    init: function (info) {
        this._minlength = info.minlength || 1;
        this._minwords = info.minwords || 1;
        this._minclasses = info.minclasses || 1;
    },
    toString: function () {
        var msgs = [];
        if (this._minlength > 1) {
            msgs.push(_.str.sprintf(_t("at least %d characters"), this._minlength));
        }
        if (this._minwords > 1) {
            msgs.push(_.str.sprintf(_t("at least %d words"), this._minwords));
        }
        if (this._minclasses > 1) {
            msgs.push(_.str.sprintf(_t("at least %d character classes"), this._minclasses));
        }
        return msgs.join(', ')
    },
    score: function (password) {
        var lengthscore = Math.min(
            password.length / this._minlength,
            1.0);
        // we want the number of "words". Splitting on no-words doesn't work
        // because JS will add an empty string when matching a leading or
        // trailing pattern e.g. " foo ".split(/\W+/) will return ['', 'foo', '']
        // by splitting on the words, we should always get wordscount + 1
        var wordscore =  Math.min(
            // \w includes _ which we don't want, so combine \W and _ then
            // invert it to know what "word" is
            //
            // Sadly JS is absolute garbage, so this splitting is basically
            // solely ascii-based unless we want to include cset
            // (http://inimino.org/~inimino/blog/javascript_cset) which can
            // generate non-trivial character-class-set-based regex patterns
            // for us. We could generate the regex statically but they're huge
            // and gnarly as hell.
            (password.split(/[^\W_]+/).length - 1) / this._minwords,
            1.0
        );
        // See above for issues pertaining to character classification:
        // we'll classify using the ascii range because that's basically our
        // only option
        var classes =
              ((/[a-z]/.test(password)) ? 1 : 0)
            + ((/[A-Z]/.test(password)) ? 1 : 0)
            + ((/\d/.test(password)) ? 1 : 0)
            + ((/[^A-Za-z\d]/.test(password)) ? 1 : 0);
        var classesscore = Math.min(classes / this._minclasses, 1.0);

        return lengthscore * wordscore * classesscore;
    },
});

return {
    /**
     * Computes the password's score, should be roughly continuous, under 0.5
     * if the requirements don't pass and at 1 if the recommendations are
     * exceeded
     */
    computeScore: function (password, requirements, recommendations) {
        var req = requirements.score(password);
        var rec = recommendations.score(password);
        return Math.pow(req, 4) * (0.5 + Math.pow(rec, 2) / 2);
    },
    Policy: Policy,
    // Recommendations from Shay (2016):
    // Our research has shown that there are other policies that are more
    // usable and more secure. We found three policies (2class12, 3class12,
    // and 2word16) that we can directly recommend over comp8
    //
    // Since 2class12 is a superset of 3class12 and 2word16, either pick it or
    // pick the other two (and get the highest score of the two). We're
    // picking the other two.
    recommendations: {
        score: function (password) {
            return _.max(_.invoke(this.policies, 'score', password));
        },
        policies: [
            new Policy({minlength: 16, minwords: 2}),
            new Policy({minlength: 12, minclasses: 3})
        ]
    }
}
});

odoo.define('auth_password_policy.Meter', function (require) {
"use strict";
var core = require('web.core');
var policy = require('auth_password_policy');
var Widget = require('web.Widget');
var _t = core._t;

var PasswordPolicyMeter = Widget.extend({
    tagName: 'meter',
    className: 'o_password_meter',
    attributes: {
        min: 0,
        low: 0.5,
        high: 0.99,
        max: 1,
        value: 0,
        optimum: 1,
    },
    init: function (parent, required, recommended) {
        this._super(parent);
        this._required = required;
        this._recommended = recommended;
    },
    start: function () {
        var helpMessage = _t("Required: %s.\n\nHint: increase length, use multiple words and use non-letter characters to increase your password's strength.");
        this.el.setAttribute(
            'title', _.str.sprintf(helpMessage, String(this._required) || _t("no requirements")));
        return this._super().then(function () {
        });
    },
    /**
     * Updates the meter with the information of the new password: computes
     * the (required x recommended) score and sets the widget's value as that
     *
     * @param {String} password
     */
    update: function (password) {
        this.el.value = policy.computeScore(password, this._required, this._recommended);
    }
});
return PasswordPolicyMeter;
});
