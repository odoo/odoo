import { expect, test } from "@odoo/hoot";
import { getLNATargetAddressSpace } from "@point_of_sale/app/utils/init_lna";

test("targetAddressSpace local", () => {
    expect(getLNATargetAddressSpace("http://192.168.1.1")).toBe("local");
    expect(getLNATargetAddressSpace("http://192.168.1.1:8008")).toBe("local");
    expect(getLNATargetAddressSpace("http://192.168.1.1:8080/demo")).toBe("local");

    expect(getLNATargetAddressSpace("invalidurl")).toBe("local");
});

test("targetAddressSpace loopback", () => {
    expect(getLNATargetAddressSpace("http://localhost")).toBe("loopback");
    expect(getLNATargetAddressSpace("http://localhost:1234/demo")).toBe("loopback");
    expect(getLNATargetAddressSpace("http://localhost/demo")).toBe("loopback");

    expect(getLNATargetAddressSpace("http://127.0.0.1")).toBe("loopback");
    expect(getLNATargetAddressSpace("http://127.0.0.1:1234/demo")).toBe("loopback");
    expect(getLNATargetAddressSpace("http://127.0.0.1/demo")).toBe("loopback");
});
