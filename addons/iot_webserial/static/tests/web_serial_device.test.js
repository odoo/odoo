import { describe, expect, test } from "@odoo/hoot";
import { WebSerialDevice } from "../src/web_serial_device";
import { FakeSerialPort } from "./fake_serial_port";

describe.current.tags("headless");

class FakeDevice extends WebSerialDevice {
    get serialPortOptions() {
        return { baudRate: 9600 };
    }

    supported() {
        return true;
    }
}

test("opens serial port", async () => {
    const port = new FakeSerialPort();
    const device = new FakeDevice(port);

    await device.open();

    expect(port.isOpen).toBe(true);
    expect(port.options.baudRate).toBe(9600);
});

test("writes to serial port", async () => {
    const port = new FakeSerialPort();
    const device = new FakeDevice(port);

    await device.open();
    await device.write("hello");

    await port.expectWrite("hello");
});

test("reads from serial port until a terminator", async () => {
    const port = new FakeSerialPort();
    const device = new FakeDevice(port);
    await device.open();

    let readPending = true;
    const readPromise = device.readUntil("world").then((result) => {
        readPending = false;
        return result;
    });

    expect(readPending).toBe(true);
    await port.simulateResponse("hello");
    expect(readPending).toBe(true);
    await port.simulateResponse(" world");
    expect(readPending).toBe(false);
    await expect(readPromise).resolves.toBe("hello world");
});
