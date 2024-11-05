const oeStructureSelector = "#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]";
const oeFieldSelector = "#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])";
export const OE_RECORD_COVER_SELECTOR = "#wrapwrap .o_record_cover_container[data-res-model]";
const oeCoverSelector = `#wrapwrap .s_cover[data-res-model], ${OE_RECORD_COVER_SELECTOR}`;
export const SAVABLE_SELECTOR = `${oeStructureSelector}, ${oeFieldSelector}, ${oeCoverSelector}`;
