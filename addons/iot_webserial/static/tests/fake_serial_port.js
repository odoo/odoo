import { expect, microTick } from "@odoo/hoot";

export class FakeSerialPort {
    constructor() {
        this.isOpen = false;
        this.options = null;
        this.dataPending = Promise.withResolvers();
        this.readable = new ReadableStream({
            pull: async (controller) => {
                // eslint-disable-next-line no-constant-condition
                while (true) {
                    const message = await this.dataPending.promise;
                    controller.enqueue(new TextEncoder().encode(message));
                    this.dataPending = Promise.withResolvers();
                }
            },
        });
        this.writable = new WritableStream({
            write: (chunk) => {
                this.writeBuffer += new TextDecoder().decode(chunk);
            },
        });
        this.writeBuffer = "";
    }

    async simulateResponse(response) {
        this.dataPending.resolve(response);
        await microTick();
    }

    async expectWrite(expectedMessage) {
        await microTick();
        expect(this.writeBuffer.startsWith(expectedMessage)).toBe(true);
        this.writeBuffer = this.writeBuffer.slice(expectedMessage.length);
    }

    open(options) {
        this.options = options;
        this.isOpen = true;
    }

    close() {
        this.isOpen = false;
    }
}
