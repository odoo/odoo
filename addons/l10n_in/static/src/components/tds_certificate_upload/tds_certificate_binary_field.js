import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";

export class TdsCertificateBinaryField extends BinaryField {
	static template = "l10n_in.TdsCertificateBinaryField";
}

export const tdsCertificateBinaryField = {
	...binaryField,
	component: TdsCertificateBinaryField,
}

registry.category("fields").add("tds_binary_field", tdsCertificateBinaryField);
