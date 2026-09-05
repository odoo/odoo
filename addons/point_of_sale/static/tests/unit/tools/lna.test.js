import { describe, expect, test } from "@odoo/hoot";
import { getLNATargetAddressSpace, isLocalHTTP } from "@point_of_sale/app/utils/init_lna";

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

describe("isLocalHTTP", () => {
    test("loopback hosts over http", () => {
        expect(isLocalHTTP("http://localhost")).toBe(true);
        expect(isLocalHTTP("http://localhost:8080/status")).toBe(true);
        expect(isLocalHTTP("http://LOCALHOST")).toBe(true); // hostname is case-insensitive
        expect(isLocalHTTP("http://127.0.0.1")).toBe(true);
        expect(isLocalHTTP("http://127.1.2.3:9100/print?x=1")).toBe(true);
        expect(isLocalHTTP("http://[::1]")).toBe(true);
        expect(isLocalHTTP("http://[::1]:8080")).toBe(true);
    });

    test("private IPv4 ranges over http", () => {
        expect(isLocalHTTP("http://10.0.0.5")).toBe(true);
        expect(isLocalHTTP("http://10.255.255.255:631")).toBe(true);
        expect(isLocalHTTP("http://192.168.1.1")).toBe(true);
        expect(isLocalHTTP("http://192.168.0.42:8008/demo")).toBe(true);
        expect(isLocalHTTP("http://169.254.10.20")).toBe(true); // link-local
        // 172.16.0.0 – 172.31.255.255
        expect(isLocalHTTP("http://172.16.0.1")).toBe(true);
        expect(isLocalHTTP("http://172.20.5.5")).toBe(true);
        expect(isLocalHTTP("http://172.31.255.254")).toBe(true);
    });

    test("172.x boundaries", () => {
        expect(isLocalHTTP("http://172.15.0.1")).toBe(false);
        expect(isLocalHTTP("http://172.32.0.1")).toBe(false);
    });

    test("other near-miss IPv4", () => {
        expect(isLocalHTTP("http://9.0.0.1")).toBe(false);
        expect(isLocalHTTP("http://11.0.0.1")).toBe(false);
        expect(isLocalHTTP("http://192.167.1.1")).toBe(false);
        expect(isLocalHTTP("http://192.169.1.1")).toBe(false);
        expect(isLocalHTTP("http://0.0.0.0")).toBe(false);
    });

    test("public hosts", () => {
        expect(isLocalHTTP("http://8.8.8.8")).toBe(false);
        expect(isLocalHTTP("http://example.com")).toBe(false);
        expect(isLocalHTTP("http://odoo.com:80/web")).toBe(false);
    });

    test("non-http schemes are never local", () => {
        expect(isLocalHTTP("https://localhost")).toBe(false);
        expect(isLocalHTTP("https://192.168.1.1")).toBe(false);
        expect(isLocalHTTP("ftp://127.0.0.1")).toBe(false);
        expect(isLocalHTTP("ws://192.168.1.1:8080")).toBe(false);
    });

    test("malformed input returns false instead of throwing", () => {
        expect(isLocalHTTP("")).toBe(false);
        expect(isLocalHTTP("not a url")).toBe(false);
        expect(isLocalHTTP("192.168.1.1")).toBe(false);
        expect(isLocalHTTP(undefined)).toBe(false);
        expect(isLocalHTTP(null)).toBe(false);
    });

    test("stays correct past the cache size limit", () => {
        for (let i = 0; i < 100; i++) {
            expect(isLocalHTTP(`http://10.0.${Math.floor(i / 256)}.${i % 256}:8080`)).toBe(true);
            expect(isLocalHTTP(`http://93.184.216.${i % 256}/p${i}`)).toBe(false);
        }
        expect(isLocalHTTP("http://10.0.0.0:8080")).toBe(true);
    });
});
