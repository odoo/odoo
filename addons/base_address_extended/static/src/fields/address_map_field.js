import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { AddressMap } from "../components/address_map";

export class AddressMapField extends AddressMap {
    static props = {
        ...standardFieldProps,
        latitude: { type: Number, optional: true },
        longitude: { type: Number, optional: true },
        address: { type: String, optional: true },
    };

    setup() {
        super.setup();
    }
}

registry.category("fields").add("address_map", AddressMapField);
