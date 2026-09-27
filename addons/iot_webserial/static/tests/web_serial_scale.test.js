import { advanceTime, describe, expect, test } from "@odoo/hoot";
import { FakeSerialPort } from "@iot_webserial/../tests/fake_serial_port";
import { WebSerialScale } from "@iot_webserial/web_serial_scale";

describe.current.tags("headless");

const openScale = async () => {
    const port = new FakeSerialPort();
    const scale = new WebSerialScale(port);
    const openPromise = scale.open();
    await port.simulateResponse("\x02E\rhelloF");
    await openPromise;
    port.writeBuffer = "";
    return { port, scale };
};

test("opens scale if correct response is received", async () => {
    const port = new FakeSerialPort();
    const scale = new WebSerialScale(port);

    const openPromise = scale.open();

    await port.expectWrite("Ehello");
    await port.simulateResponse("\x02E\rhello");
    await port.expectWrite("F");
    await port.simulateResponse("F");
    expect(openPromise).resolves.toBe(true);
});

test("does not open scale if bad response is received", async () => {
    const port = new FakeSerialPort();
    const scale = new WebSerialScale(port);

    const openPromise = scale.open();

    await port.expectWrite("Ehello");
    await port.simulateResponse("NOT A SCALE");
    expect(openPromise).resolves.toBe(false);
});

test("reads gross weight", async () => {
    const { port, scale } = await openScale();

    const weightPromise = scale.readWeight();

    await port.expectWrite("W");
    await port.simulateResponse("\x0201.234\r");
    await expect(weightPromise).resolves.toBe(1.234);
    expect(scale.tareEnabled).toBe(false);
});

test("reads net weight", async () => {
    const { port, scale } = await openScale();

    const weightPromise = scale.readWeight();

    await port.expectWrite("W");
    await port.simulateResponse("\x0201.234N\r");
    await expect(weightPromise).resolves.toBe(1.234);
    expect(scale.tareEnabled).toBe(true);
});

test("retries reading if the scale is in motion", async () => {
    const { port, scale } = await openScale();

    const weightPromise = scale.readWeight();

    await port.expectWrite("W");
    await port.simulateResponse("\x02?\x01\r");
    await advanceTime(100);
    await port.expectWrite("W");
    await port.simulateResponse("\x0201.234\r");
    await expect(weightPromise).resolves.toBe(1.234);
});

test("returns 0 on status response if tare has just been enabled", async () => {
    const { port, scale } = await openScale();

    const weightPromise = scale.readWeight();

    await port.expectWrite("W");
    await port.simulateResponse("\x02?\x30\r");
    await expect(weightPromise).resolves.toBe(0);
    expect(scale.tareEnabled).toBe(true);
});

test("returns null on status response if tare is already enabled", async () => {
    const { port, scale } = await openScale();
    scale.tareEnabled = true;

    const weightPromise = scale.readWeight();

    await port.expectWrite("W");
    await port.simulateResponse("\x02?\x30\r");
    await expect(weightPromise).resolves.toBe(null);
    expect(scale.tareEnabled).toBe(true);
});

test("returns null for any other status response", async () => {
    const { port, scale } = await openScale();

    const weightPromise = scale.readWeight();

    await port.expectWrite("W");
    await port.simulateResponse("\x02?\x02\r");
    await expect(weightPromise).resolves.toBe(null);
});
