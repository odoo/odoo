import { expect, test } from "@odoo/hoot";
import { ScaleInterface } from "@point_of_sale/app/utils/scale/scale_interface";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const TEST_PRICE_PER_KG = 1.5;
const TEST_DECIMAL_ACCURACY = 2;
const NBSP = "\xa0";

const setupScale = async () => {
    const posStore = await setupPosEnv();
    const scale = new ScaleInterface(posStore);
    scale.setProduct({ display_name: "Test product" }, TEST_DECIMAL_ACCURACY, TEST_PRICE_PER_KG);
    return scale;
};

test("starts with all zero weights", async () => {
    const scale = await setupScale();

    expect(scale.weight).toBe(0);
    expect(scale.tareWeight).toBe(0);
    expect(scale.netWeight).toBe(0);
});

test("subtracts tare from gross to get net", async () => {
    const scale = await setupScale();

    scale.weight = 7;
    scale.tare = 5;

    expect(scale.netWeight).toBe(2);
});

test("ignores tare if hardware tare is enabled", async () => {
    const scale = await setupScale();

    scale.hardwareTare = true;
    scale.weight = 7;
    scale.tare = 5;

    expect(scale.netWeight).toBe(7);
});

test("formats strings correctly", async () => {
    const scale = await setupScale();

    scale.weight = 7.53;
    scale.tare = 3.21;

    expect(scale.grossWeightString).toBe("7.53 kg");
    expect(scale.tareWeightString).toBe("3.21 kg");
    expect(scale.netWeightString).toBe("4.32 kg");
    expect(scale.unitPriceString).toBe(`$${NBSP}1.50 / kg`);
    expect(scale.totalPriceString).toBe(`$${NBSP}6.48`);
});

test("rounds net weight to product unit", async () => {
    const scale = await setupScale();

    scale.weight = 1.556;
    scale.tare = 0.501;

    expect(scale.netWeight).toBe(1.06);
    scale.product.decimalAccuracy = 3;
    expect(scale.netWeight).toBe(1.055);
});

test("weight is invalid when zero", async () => {
    const scale = await setupScale();

    expect(scale.isWeightValid).toBe(false);
});

test("weight is invalid when negative", async () => {
    const scale = await setupScale();

    scale.weight = 1;
    scale.tare = 2;

    expect(scale.isWeightValid).toBe(false);
});

test("weight is invalid when the same as last weight", async () => {
    const scale = await setupScale();

    scale.weight = 1;

    expect(scale.isWeightValid).toBe(true);
    scale.confirmWeight();
    expect(scale.isWeightValid).toBe(false);
});

test("requesting tare immediately copies weight if valid", async () => {
    const scale = await setupScale();

    scale.weight = 1;
    scale.requestTare();

    expect(scale.tareRequested).toBe(false);
    expect(scale.tare).toBe(1);
});

test("requesting tare waits for next valid weight", async () => {
    const scale = await setupScale();

    scale.requestTare();

    expect(scale.tareRequested).toBe(true);
    scale._setWeight(1);
    expect(scale.tareRequested).toBe(false);
    expect(scale.tare).toBe(1);
});
