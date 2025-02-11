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
    comp(a, b, { precision, method } = {}) {
        return comp(a, b, {
            precision: precision || this.precision,
            method: method || this.method,
        });
    }

    isZero(a, { precision, method } = {}) {
        return this.comp(a, 0, { precision, method }) === EQ;
    }

    isPositive(a, { precision, method } = {}) {
        return this.comp(a, 0, { precision, method }) === GT;
    }

    isNegative(a, { precision, method } = {}) {
        return this.comp(a, 0, { precision, method }) === LT;
    }

    equal(a, b, { precision, method } = {}) {
        return this.comp(a, b, { precision, method }) === EQ;
    }

    /**
     * Symmetric rounding.
     * ```
     * round(1.23, { precision: 0.1, method: "UP" }) // 1.3
     * round(-1.23, { precision: 0.1, method: "UP" }) // -1.3
     * ```
     */
    round(a, { precision, method } = {}) {
        return roundPrecision(a, precision || this.precision, method || this.method);
    }

    /**
     * ```
     * asymmetricRound(1.23, { precision: 0.1, method: "UP" }) // 1.3
     * asymmetricRound(-1.23, { precision: 0.1, method: "UP" }) // -1.2
     * ```
     */
    asymmetricRound(a, { precision, method } = {}) {
        method = method ?? this.method ?? "HALF-UP";
        return roundPrecision(
            a,
            precision || this.precision,
            // If negative, invert the rounding method
            this.isNegative(a, { precision, method }) ? invertMethod(method) : method
        );
    }
}
