import { loadImage } from "@pos_restaurant/app/services/floor_plan/utils/utils";

export function selectImage() {
    return new Promise((resolve) => {
        const input = document.createElement("input");

        function onEnd(data) {
            document.body.removeChild(input);
            resolve(data);
        }

        input.type = "file";
        input.accept = "image/*";
        input.style.display = "none";
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) {
                return onEnd();
            }
            const objectUrl = URL.createObjectURL(file);
            loadImage(objectUrl).then((data) => {
                if (data) {
                    onEnd({ ...data, objectUrl, name: file.name });
                } else {
                    URL.revokeObjectURL(objectUrl);
                    onEnd();
                }
            });
        };

        document.body.appendChild(input);
        input.click();
    });
}
