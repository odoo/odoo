import { test, describe, expect } from "@odoo/hoot";
import { convertRawToDate, convertDateToRaw } from "@point_of_sale/app/models/related_models/utils";
const { DateTime } = luxon;

describe("Date conversion utilities", () => {
    const mockModel = { model: "test.model" };

    test("convertRawToDate", () => {
        const rawDate = "2023-12-25";
        const result = convertRawToDate(mockModel, rawDate, "date_field");
        expect(result).toBeInstanceOf(DateTime);
        expect(result.isValid).toBe(true);
        expect(convertRawToDate(mockModel, null, "date_field")).toBe(undefined);
        expect(convertRawToDate(mockModel, undefined, "date_field")).toBe(undefined);
        expect(() => convertRawToDate(mockModel, "invalid", "date_field")).toThrow();
    });

    test("convertDateToRaw", () => {
        const dateTime = DateTime.fromISO("2023-12-25");
        const result = convertDateToRaw(dateTime);
        expect(result).toBe("2023-12-25"); // directly check the string value
        expect(convertDateToRaw(null)).toBe(undefined);
        expect(convertDateToRaw(undefined)).toBe(undefined);
        expect(convertDateToRaw("2023-12-25")).toBe("2023-12-25"); // should return the same string
    });
});
