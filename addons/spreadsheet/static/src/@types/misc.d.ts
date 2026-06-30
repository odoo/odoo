declare module "@spreadsheet" {
    export interface Zone {
        bottom: number;
        left: number;
        right: number;
        top: number;
    }

    export interface LazyTranslatedString extends String {}
}
