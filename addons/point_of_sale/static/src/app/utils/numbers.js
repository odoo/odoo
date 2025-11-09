import { roundPrecision } from "@web/core/utils/numbers";
import { Base } from "@point_of_sale/app/models/related_models";

export const LT = -1;
export const EQ = 0;
export const GT = 1;

export function comp(a, b, { precision = 1, method = "HALF-UP" } = {}) {
    a = roundPrecision(a, precision, method);
    b = roundPrecision(b, precision, method);
    const d = a - b;
    if (d === 0 || roundPrecision(d, precision, method) === 0) {
        return EQ;
    }
    return d < 0 ? LT : GT;
}

function invertMethod(method) {
    return method === "UP"
        ? "DOWN"
        : method === "DOWN"
        ? "UP"
        : method === "HALF-UP"
        ? "HALF-DOWN"
        : method === "HALF-DOWN"
        ? "HALF-UP"
        : method;
}

export class AbstractNumbers extends Base {
    get precision() {
        return Math.pow(10, -2);
    }

    get method() {
        return "HALF-UP";
    }

    comp(a, b) {
        return comp(a, b, {
            precision: this.precision,
            method: this.method,
        });
    }

    isZero(a) {
        return this.comp(a, 0) === EQ;
    }

    isPositive(a) {
        return this.comp(a, 0) === GT;
    }

    isNegative(a) {
        return this.comp(a, 0) === LT;
    }

    equal(a, b) {
        return this.comp(a, b) === EQ;
    }

    /**
     * Symmetric rounding.
     * ```
     * round(1.23, { precision: 0.1, method: "UP" }) // 1.3
     * round(-1.23, { precision: 0.1, method: "UP" }) // -1.3
     * ```
     */
    round(a) {
        return roundPrecision(a, this.precision, this.method);
    }

    asymmetricRound(a) {
        return roundPrecision(
            a,
            this.precision,
            // If negative, invert the rounding method
            this.isNegative(a) ? invertMethod(this.method) : this.method
        );
    }
}
