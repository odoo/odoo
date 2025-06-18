import { expect, test } from "@odoo/hoot";
import { FieldOperator } from "@web/core/utils/field_operator";

test("operator is valid", () => {
    expect(new FieldOperator("+1", "brol").isValid).toBe(false);
    expect(new FieldOperator("/0", "float").isValid).toBe(false);
    expect(new FieldOperator("/0", "int").isValid).toBe(false);
    expect(new FieldOperator("/0", "monetary").isValid).toBe(false);
});

test("operations on int", () => {
    let op = new FieldOperator("+=1.5", "int");
    expect(op.isValid).toBe(false);
    op = new FieldOperator("+=1", "int");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(1);
    expect(op.operator).toBe("+");
    op = new FieldOperator("-=0", "int");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(0);
    expect(op.operator).toBe("-");
    op = new FieldOperator("/=2", "int");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(2);
    expect(op.operator).toBe("/");
    op = new FieldOperator("*=4", "int");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(4);
    expect(op.operator).toBe("*");
});

test("operations on float or monetary", () => {
    let op = new FieldOperator("-=2.65678909876545", "monetary");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(2.66);
    expect(op.operator).toBe("-");
    op = new FieldOperator("-=2.65678909876545", "float");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(2.6567891);
    expect(op.operator).toBe("-");
    op = new FieldOperator("/=2.65678909876545", "monetary");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(2.66);
    expect(op.operator).toBe("/");
    op = new FieldOperator("/=2.65678909876545", "float");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(2.6567891);
    expect(op.operator).toBe("/");
    op = new FieldOperator("*=PI", "float");
    expect(op.isValid).toBe(true);
    expect(op.increment).toBe(Math.PI);
    expect(op.operator).toBe("*");
});
