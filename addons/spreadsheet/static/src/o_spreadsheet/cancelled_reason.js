/**
 * @enum {string}
 */
export const CommandResult = {
    Success: "Success", // should be imported from o-spreadsheet instead of redefined here
    FilterNotFound: "FilterNotFound",
    InvalidFilterMove: "InvalidFilterMove",
    DuplicatedFilterLabel: "DuplicatedFilterLabel",
    InvalidFilterLabel: "InvalidFilterLabel",
    PivotCacheNotLoaded: "PivotCacheNotLoaded",
    InvalidValueTypeCombination: "InvalidValueTypeCombination",
    ListIdDuplicated: "ListIdDuplicated",
    InvalidNextId: "InvalidNextId",
    ListIdNotFound: "ListIdNotFound",
    EmptyName: "EmptyName",
    PivotIdNotFound: "PivotIdNotFound",
    InvalidFieldMatch: "InvalidFieldMatch",
};
