import { expect, test } from "@odoo/hoot";

import { datasetFromElements} from "@sign/components/sign_request/document_signable";

test("check datasetFromElements parsing", async () => {
    const backend_element = document.createElement("input");
        backend_element.dataset.name = "Text";
        backend_element.dataset.id = "36";
        backend_element.dataset.value = "123456789123456789";  // > Number.MAX_SAFE_INTEGER

        const backend_element_2 = document.createElement("input");
        backend_element_2.dataset.name = "Text";
        backend_element_2.dataset.value = "14";

        const backend_element_3 = document.createElement("input");
        backend_element_3.dataset.name = "Text";
        backend_element_3.dataset.value = "Some text entered by the user!";

        expect(datasetFromElements([backend_element, backend_element_2, backend_element_3])).toEqual([
            {
                "name": "Text",
                "id": 36,
                "value": "123456789123456789",
            },
            {
                "name": "Text",
                "value": 14,
            },
            {
                "name": "Text",
                "value": "Some text entered by the user!",
            },
        ]);
});
