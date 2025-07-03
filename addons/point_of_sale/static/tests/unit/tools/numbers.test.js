import { expect, test } from "@odoo/hoot";
import { EQ, AbstractNumbers } from "@point_of_sale/app/utils/numbers";

class CustomNumbers extends AbstractNumbers {
    constructor() {
        super({});
    }
    get precision() {
        return 0.05;
    }
    get method() {
        return "UP";
    }
}

const numbers = new CustomNumbers();

test.tags("pos");
test("inputs are rounded before comparison", () => {
    expect(numbers.comp(1.24, 1.21)).toBe(EQ);
    expect(numbers.isZero(1.24 - 1.21)).toBe(false);
});

test.tags("pos");
test("rounding", () => {
    expect(numbers.round(1.28)).toBe(1.3);
    expect(numbers.round(-1.28)).toBe(-1.3);
    expect(numbers.asymmetricRound(1.28)).toBe(1.3);
    expect(numbers.asymmetricRound(-1.28)).toBe(-1.25);
});
