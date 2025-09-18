// @ts-check

/** @module @web/model/relational_model/operation - Arithmetic operation class for numeric field transformations */

export class Operation {
    /**
     * @param {"+" | "-" | "*" | "/"} operator
     * @param {number} operand
     */
    constructor(operator, operand) {
        this.operator = operator;
        this.operand = operand;
    }

    /**
     * @param {number} value
     * @returns {number}
     */
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
