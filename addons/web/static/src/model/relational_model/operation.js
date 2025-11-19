import { smartDateUnits } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { escapeRegExp } from "@web/core/utils/strings";
export class Operation {
    static supportedOperators = [];
    static parse() {}
    /**
     * @param {string} operator
     * @param {*} operand
     */
    constructor(operator, operand) {
        this.operator = operator;
        this.operand = operand;
        if (!this.constructor.supportedOperators.includes(this.operator)) {
            throw new Error(`Operator ${this.operator} not supported on ${this.constructor.name}`);
        }
        this.setup();
    }

    setup() {}

    toString() {
        return `${this.operator} ${this.operand}`;
    }
}

export class DateTimeOperation extends Operation {
    static supportedOperators = ["+", "-"];
    static dateTimeUnits = Object.keys(smartDateUnits).join();

    static parse(operation) {
        if (!operation) {
            return false;
        }
        const regex = new RegExp(
            `^(?<operator>[+\\-])\\s*=\\s*(?<amount>\\d+)\\s*(?<unit>[${DateTimeOperation.dateTimeUnits}])?$`
        );
        const match = operation.match(regex);
        if (match?.groups) {
            const amount = match.groups.amount;
            const unit = match.groups.unit || "d";
            const operand = {
                amount: parseInt(amount, 10),
                unit,
            };
            const operator = match.groups.operator;
            return new DateTimeOperation(operator, operand);
        }
        return false;
    }

    setup() {
        this.amount = this.operand.amount;
        this.unit = this.operand.unit;
        this.luxonUnit = smartDateUnits[this.unit];
    }

    compute(value) {
        if (!value) {
            return;
        }
        const delta = { [this.luxonUnit]: this.amount };
        return this.operator === "+" ? value.plus(delta) : value.minus(delta);
    }

    toString() {
        return `${this.operator} ${this.amount} ${this.luxonUnit}`;
    }
}

export class ArithmeticOperation extends Operation {
    static supportedOperators = ["+", "-", "/", "*"];

    static parse(operation, parseValueFn) {
        if (!operation) {
            return false;
        }
        if (typeof parseValueFn !== "function") {
            return false;
        }
        const regex = new RegExp(
            `^(?<operator>[+\\-*/])\\s*=\\s*(?<operand>-?\\d+(?:[${escapeRegExp(
                localization.decimalPoint
            )}]\\d+)?)$`
        );
        const match = operation.match(regex);
        if (match?.groups) {
            const operand = parseValueFn(match.groups.operand);
            const operator = match.groups.operator;
            return new ArithmeticOperation(operator, operand);
        }
        return false;
    }

    compute(value) {
        switch (this.operator) {
            case "+":
                return value + this.operand;
            case "-":
                return value - this.operand;
            case "*":
                return value * this.operand;
            case "/":
                return value / this.operand;
            default:
                throw new Error(`Unsupported operator: ${this.operator}`);
        }
    }
}
