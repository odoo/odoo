import { expect, test } from "@odoo/hoot";
import { getLNATargetAddressSpace, isPrivateIp } from "@point_of_sale/app/utils/init_lna";

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

test("isPrivateIp: private and loopback ranges", () => {
    expect(isPrivateIp("10.0.0.0")).toBe(true);
    expect(isPrivateIp("10.255.255.255")).toBe(true);
    expect(isPrivateIp("127.0.0.1")).toBe(true);
    expect(isPrivateIp("169.254.1.1")).toBe(true);
    expect(isPrivateIp("172.16.0.1")).toBe(true);
    expect(isPrivateIp("172.31.255.255")).toBe(true);
    expect(isPrivateIp("192.168.0.1")).toBe(true);
});

test("isPrivateIp: public addresses", () => {
    expect(isPrivateIp("8.8.8.8")).toBe(false);
    expect(isPrivateIp("11.0.0.1")).toBe(false);
    expect(isPrivateIp("172.15.255.255")).toBe(false);
    expect(isPrivateIp("172.32.0.0")).toBe(false);
    expect(isPrivateIp("192.167.0.1")).toBe(false);
    expect(isPrivateIp("192.169.0.1")).toBe(false);
    expect(isPrivateIp("169.253.0.1")).toBe(false);
});

test("isPrivateIp: invalid values", () => {
    expect(isPrivateIp("192.168.1")).toBe(false);
    expect(isPrivateIp("192.168.1.1.1")).toBe(false);
    expect(isPrivateIp("192.168.1.256")).toBe(false);
    expect(isPrivateIp("192.168.-1.1")).toBe(false);
    expect(isPrivateIp("192.168.a.1")).toBe(false);
    expect(isPrivateIp("localhost")).toBe(false);
    expect(isPrivateIp("::1")).toBe(false);
    expect(isPrivateIp("")).toBe(false);
    expect(isPrivateIp(undefined)).toBe(false);
    expect(isPrivateIp(null)).toBe(false);
    expect(isPrivateIp(192168001001)).toBe(false);
});
