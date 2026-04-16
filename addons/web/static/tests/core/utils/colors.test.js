import { convertHslToRgb, convertRgbToHsl } from "@web/core/utils/colors";
import { expect, test } from "@odoo/hoot";

test("convertRgbToHsl should convert RGB to HSL correctly", () => {
    // Pure red
    expect(convertRgbToHsl(255, 0, 0)).toEqual({ hue: 0, saturation: 100, lightness: 50 });
    
    // Pure green
    expect(convertRgbToHsl(0, 255, 0)).toEqual({ hue: 120, saturation: 100, lightness: 50 });
    
    // Pure blue
    expect(convertRgbToHsl(0, 0, 255)).toEqual({ hue: 240, saturation: 100, lightness: 50 });
    
    // White
    expect(convertRgbToHsl(255, 255, 255)).toEqual({ hue: 0, saturation: 0, lightness: 100 });
    
    // Black
    expect(convertRgbToHsl(0, 0, 0)).toEqual({ hue: 0, saturation: 0, lightness: 0 });
    
    // Gray (should have 0 saturation)
    const gray = convertRgbToHsl(128, 128, 128);
    expect(gray.saturation).toBe(0);
    expect(Math.round(gray.lightness)).toBe(50);
});

test("convertHslToRgb should convert HSL to RGB correctly", () => {
    // Pure red
    expect(convertHslToRgb(0, 100, 50)).toEqual({ red: 255, green: 0, blue: 0 });
    
    // Pure green
    expect(convertHslToRgb(120, 100, 50)).toEqual({ red: 0, green: 255, blue: 0 });
    
    // Pure blue
    expect(convertHslToRgb(240, 100, 50)).toEqual({ red: 0, green: 0, blue: 255 });
    
    // White
    expect(convertHslToRgb(0, 0, 100)).toEqual({ red: 255, green: 255, blue: 255 });
    
    // Black
    expect(convertHslToRgb(0, 0, 0)).toEqual({ red: 0, green: 0, blue: 0 });
});

test("convertHslToRgb with saturation=0 should produce true grayscale", () => {
    // Test various hues with saturation=0 - all should produce grayscale (R=G=B)
    const testCases = [
        { hue: 0, lightness: 50, expectedGray: 128 },
        { hue: 45, lightness: 50, expectedGray: 128 },
        { hue: 90, lightness: 25, expectedGray: 64 },
        { hue: 135, lightness: 75, expectedGray: 191 },
        { hue: 180, lightness: 50, expectedGray: 128 },
        { hue: 225, lightness: 50, expectedGray: 128 },
        { hue: 270, lightness: 90, expectedGray: 230 },
        { hue: 315, lightness: 10, expectedGray: 26 },
        { hue: 359, lightness: 50, expectedGray: 128 },
    ];
    
    testCases.forEach(({ hue, lightness, expectedGray }) => {
        const rgb = convertHslToRgb(hue, 0, lightness);
        // All RGB components should be equal for grayscale
        expect(rgb.red).toBe(rgb.green);
        expect(rgb.green).toBe(rgb.blue);
        expect(rgb.red).toBe(expectedGray);
    });
});

test("convertHslToRgb with near-zero saturation should produce true grayscale", () => {
    // Test with extremely small saturation values (< 0.01%) - should still produce grayscale
    const rgb1 = convertHslToRgb(123, 0.001, 50);
    expect(rgb1.red).toBe(rgb1.green);
    expect(rgb1.green).toBe(rgb1.blue);
    
    const rgb2 = convertHslToRgb(234, 0.005, 75);
    expect(rgb2.red).toBe(rgb2.green);
    expect(rgb2.green).toBe(rgb2.blue);
});

test("HSL to RGB and back should preserve values", () => {
    // Test round-trip conversion
    const testColors = [
        { r: 255, g: 0, b: 0 },     // Red
        { r: 0, g: 255, b: 0 },     // Green
        { r: 0, g: 0, b: 255 },     // Blue
        { r: 255, g: 255, b: 0 },   // Yellow
        { r: 255, g: 0, b: 255 },   // Magenta
        { r: 0, g: 255, b: 255 },   // Cyan
        { r: 128, g: 128, b: 128 }, // Gray
        { r: 192, g: 64, b: 32 },   // Brown-ish
    ];
    
    testColors.forEach(({ r, g, b }) => {
        const hsl = convertRgbToHsl(r, g, b);
        const rgb = convertHslToRgb(hsl.hue, hsl.saturation, hsl.lightness);
        
        // Allow for small rounding errors (±1)
        expect(Math.abs(rgb.red - r) <= 1).toBe(true);
        expect(Math.abs(rgb.green - g) <= 1).toBe(true);
        expect(Math.abs(rgb.blue - b) <= 1).toBe(true);
    });
});

test("convertHslToRgb should handle edge cases", () => {
    // Invalid inputs should return false
    expect(convertHslToRgb(-1, 50, 50)).toBe(false);
    expect(convertHslToRgb(361, 50, 50)).toBe(false);
    expect(convertHslToRgb(180, -1, 50)).toBe(false);
    expect(convertHslToRgb(180, 101, 50)).toBe(false);
    expect(convertHslToRgb(180, 50, -1)).toBe(false);
    expect(convertHslToRgb(180, 50, 101)).toBe(false);
    expect(convertHslToRgb("invalid", 50, 50)).toBe(false);
    expect(convertHslToRgb(NaN, 50, 50)).toBe(false);
});

test("convertRgbToHsl should handle edge cases", () => {
    // Invalid inputs should return false
    expect(convertRgbToHsl(-1, 128, 128)).toBe(false);
    expect(convertRgbToHsl(256, 128, 128)).toBe(false);
    expect(convertRgbToHsl(128, -1, 128)).toBe(false);
    expect(convertRgbToHsl(128, 256, 128)).toBe(false);
    expect(convertRgbToHsl(128, 128, -1)).toBe(false);
    expect(convertRgbToHsl(128, 128, 256)).toBe(false);
    expect(convertRgbToHsl("invalid", 128, 128)).toBe(false);
    expect(convertRgbToHsl(NaN, 128, 128)).toBe(false);
});

