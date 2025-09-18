/**
 * JSDoc type alias: `@param {integer}` maps to `number`.
 * Preserves semantic intent (whole numbers) in documentation.
 */
declare type integer = number;

declare const luxon: typeof import("luxon");

// Bootstrap 5 globals used by database_manager.js and other public pages
declare const Modal: any;
declare const Tooltip: any;
declare const Dropdown: any;

// declare const Qunit: typeof import("qunit"); => Because we add methods to QUnit, we define our own..
// @ts-expect-error -- QUnit type is augmented by hoot.d.ts, not the npm @types/qunit
declare const QUnit: QUnit;

// @ts-expect-error -- jQuery global is declared without a default export in @types/jquery
declare const $: typeof import("jquery");

// Third-party libraries loaded as globals
declare const ace: any;
declare const ZXing: any;
declare const FullCalendar: any;
declare const SignaturePad: any;
declare const StackTrace: {
    fromError(error: Error): Promise<Array<{ fileName: string; lineNumber: number; columnNumber: number; functionName: string }>>;
};

// Web APIs not yet in lib.dom.d.ts
declare class BarcodeDetector {
    constructor(options?: { formats?: string[] });
    detect(source: ImageBitmapSource): Promise<Array<{ rawValue: string; format: string }>>;
    static getSupportedFormats(): Promise<string[]>;
}

// Third-party globals accessed via `window.*`
interface Window {
    ace: any;
    ZXing: any;
    FullCalendar: any;
    SignaturePad: any;
    MozBlob: typeof Blob | undefined;
    WebKitBlob: typeof Blob | undefined;
    clickEverywhere: ((xmlId?: string) => Promise<void>) | undefined;
}
