import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { Field } from "@web/views/fields/field";

/**
 * คำนวณข้อความ hint ของฟิลด์หนึ่ง ๆ
 * กติกา: ใช้ override ก่อน ถ้าไม่มีให้ใช้ required (สำคัญ:) หรือฟิลด์สำคัญ (auto)
 * คืนค่า null เมื่อฟิลด์ไม่เข้าเงื่อนไข
 */
export function buildHint(config, model, name, fieldType, required) {
    if (!config || !config.enabled) {
        return null;
    }
    const isCustom = (config.custom_models || []).includes(model);
    if (!isCustom && !config.apply_core) {
        return null;
    }
    const override = config.overrides && config.overrides[model] && config.overrides[model][name];
    const important = ((config.important && config.important[model]) || []).includes(name);
    if (!override && !required && !important) {
        return null;
    }
    const auto = (config.auto && config.auto[fieldType]) || config.default;
    const kind = override ? override.kind : required ? "warning" : auto[0];
    const body = override ? override.text : auto[1];
    const prefix = (config.prefixes && config.prefixes[kind]) || "";
    return `${prefix} ${body}`.trim();
}

patch(Field.prototype, {
    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        // เฉพาะช่องที่แก้ไขได้ และ widget รองรับ placeholder และยังว่างอยู่
        if (!props.readonly && "placeholder" in props && !props.placeholder) {
            const record = this.props.record;
            const meta = record.fields[this.props.name];
            const hint = buildHint(
                session.od19_field_hints,
                record.resModel,
                this.props.name,
                this.type,
                Boolean(meta && meta.required)
            );
            if (hint) {
                props.placeholder = hint;
            }
        }
        return props;
    },
});
