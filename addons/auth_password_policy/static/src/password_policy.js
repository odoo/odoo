/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

export class Policy {
    /**
     * @param {String} password
     * @returns {number}
     */
    score(password) {}
}

export class ConcretePolicy extends Policy {
    /**
     * @param {Object} info
     * @param {Number} [info.minlength=0]
     * @param {Number} [info.minwords=0]
     * @param {Number} [info.minclasses=0]
     */
    constructor({ minlength, minwords, minclasses }) {
        super();
        this.minlength = minlength || 0;
        this.minwords = minwords || 0;
        this.minclasses = minclasses || 0;
    }
    toString() {
        const msgs = [];
        if (this.minlength > 1) {
            msgs.push(_t("at least %s characters", this.minlength));
        }
        if (this.minwords > 1) {
            msgs.push(_t("at least %s words", this.minwords));
        }
        if (this.minclasses > 1) {
            msgs.push(_t("at least %s character classes", this.minclasses));
        }
        return msgs.join(", ");
    }

    score(password) {
        if (!password) {
            return 0;
        }
        const lengthscore = Math.min(password.length / this.minlength, 1.0);
        // we want the number of "words". Splitting on no-words doesn't work
        // because JS will add an empty string when matching a leading or
        // trailing pattern e.g. " foo ".split(/\W+/) will return ['', 'foo', '']
        // by splitting on the words, we should always get wordscount + 1

        // \w includes _ which we don't want, so combine \W and _ then
        // invert it to know what "word" is
        //
        // Sadly JS is absolute garbage, so this splitting is basically
        // solely ascii-based unless we want to include cset
        // (http://inimino.org/~inimino/blog/javascript_cset) which can
        // generate non-trivial character-class-set-based regex patterns
        // for us. We could generate the regex statically but they're huge
        // and gnarly as hell.
        const wordCount = password.split(/[^\W_]+/).length - 1;
        const wordscore = this.minwords !== 0 ? Math.min(wordCount / this.minwords, 1.0) : 1.0;
        // See above for issues pertaining to character classification:
        // we'll classify using the ascii range because that's basically our
        // only option
        const classes =
            (/[a-z]/.test(password) ? 1 : 0) +
            (/[A-Z]/.test(password) ? 1 : 0) +
            (/\d/.test(password) ? 1 : 0) +
            (/[^A-Za-z\d]/.test(password) ? 1 : 0);
        const classesscore = Math.min(classes / this.minclasses, 1.0);

        return lengthscore * wordscore * classesscore;
    }
}

/**
 * Computes the password's score, should be roughly continuous, under 0.5
 * if the requirements don't pass and at 1 if the recommendations are
 * exceeded
 *
 * @param {String} password
 * @param {Policy} requirements
 * @param {Policy} recommendations
 */
export function computeScore(password, requirements, recommendations = recommendations) {
    const req = requirements.score(password);
    const rec = recommendations.score(password);
    return Math.pow(req, 4) * (0.5 + Math.pow(rec, 2) / 2);
}

/**
 * Recommendations from Shay (2016):
 *
 * > Our research has shown that there are other policies that are more usable
 * > and more secure. We found three policies (2class12, 3class12, and 2word16)
 * > that we can directly recommend over comp8
 *
 * Since 2class12 is a superset of 3class12 and 2word16, either pick it or
 * pick the other two (and get the highest score of the two). We're
 * picking the other two.
 *
 * @type Policy
 */
export const recommendations = {
    score(password) {
        return Math.max(...this.policies.map((p) => p.score(password)));
    },
    policies: [
        new ConcretePolicy({ minlength: 16, minwords: 2 }),
        new ConcretePolicy({ minlength: 12, minclasses: 3 }),
    ],
};
