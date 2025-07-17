export class Operation {
    constructor(operator, operand) {
        this.operator = operator;
        this.operand = operand;
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
