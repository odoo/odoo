import { roundDecimals } from "./numbers";

export class FieldOperator {
    _allowedTypes = ["float", "int", "monetary"];
    increment;
    unit;
    operator;
    operation;
    type;
    isValid = false;

    constructor(value, type) {
        if (!this._allowedTypes.includes(type)) {
            return;
        }

        this.type = type;
        this.operation = value.replace(/\s+/g, "");

        switch (this.type) {
            case "float":
            case "monetary":
                this._parseFloatOrMonetary();
                break;
            case "int":
                this._parseInt();
                break;
        }

        if (this.operator === "/" && this.increment === 0) {
            this.isValid = false;
        }
    }

    _parseFloatOrMonetary() {
        const regex = /^(?<operator>[%+\-*/])=(?<increment>\d+(?:[.,]\d+)?|PI)$/;
        const match = this.operation.match(regex);
        if (match?.groups) {
            this.operator = match.groups.operator;
            if (match.groups.increment === "PI") {
                this.increment = Math.PI;
                this.isValid = true;
            } else {
                const normalizedIncrement = match.groups.increment.replace(",", ".");
                const value = parseFloat(normalizedIncrement);
                if (!isNaN(value)) {
                    const decimals = this.type === "monetary" ? 2 : 8;
                    this.increment = roundDecimals(value, decimals);
                    this.isValid = true;
                }
            }
        }
    }

    _parseInt() {
        const regex = /^(?<operator>[%+\-*/])=(?<increment>\d+)$/;
        const match = this.operation.match(regex);
        if (match?.groups) {
            this.operator = match.groups.operator;
            this.increment = parseInt(match.groups.increment, 10);
            this.isValid = true;
        }
    }

    operate(value) {
        if (!this.isValid) {
            return value;
        }

        switch (this.operator) {
            case "+":
                return value + this.increment;
            case "-":
                return value - this.increment;
            case "*":
                return value * this.increment;
            case "/":
                return value / this.increment;
            case "%":
                return value % this.increment;
            default:
                throw new Error(`Unsupported operator: ${this.operator}`);
        }
    }
}
