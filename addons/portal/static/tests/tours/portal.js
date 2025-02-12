import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('portal_load_homepage', {
    url: '/my',
    steps: () => [
        {
            content: "Check portal is loaded",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
            run: "click",
        },
        {
            content: "Load my account details",
            trigger: 'input[value="Joel Willis"]',
            run: "click",
        },
        {
            content: 'type a different phone number',
            trigger: 'input[name="phone"]',
            run: "edit +1 555 666 7788",
        },
        {
            content: "Submit the form",
            trigger: 'button[type=submit]',
            run: "click",
        },
        {
            content: "Check that we are back on the portal",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
        }
    ]
});

let profilePictureSrc = "";

registry.category("web_tour.tours").add("portal_profile_update", {
    url: "/my/account",
    steps: () => [
        {
            content: "Ensure that Profile Picture for Portal user is present",
            trigger: ".o_portal_details .o_wportal_avatar_img",
        },
        {
            content: "Ensure that Edit Button is present and Update the Profile Picture",
            trigger: ".o_portal_details .o_portal_profile_pic_edit",
            run: async function () {
                profilePictureSrc = document.querySelector(
                    ".o_portal_details .o_wportal_avatar_img"
                ).src;

                const fileInputEl = document.querySelector(".o_file_upload");
                // fetching image for upload
                const response = await fetch("/portal/static/src/img/portal-addresses.svg");
                const blob = await response.blob();
                // simulating or mimicing file upload
                const simulatedImageFile = new File([blob], "portal-addresses.svg", {
                    type: blob.type,
                });
                const dataTransfer = new DataTransfer();

                dataTransfer.items.add(simulatedImageFile);
                fileInputEl.files = dataTransfer.files;

                fileInputEl.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
            },
        },
        {
            content: "Comparing previous Profile Picture with new One",
            trigger: ".o_wportal_avatar_img",
            run: function () {
                if (this.anchor.src === profilePictureSrc) {
                    throw new Error("Profile Picture is not updated!");
                }
            },
        },
        {
            content: "Click on save button",
            trigger: ".o_portal_details button[type=submit]",
            run: "click",
        },
        {
            content: "Click on edit information",
            trigger: "a:contains('Edit information')",
            run: "click",
        },
        {
            content: "Click on delete button",
            trigger: ".o_portal_details .o_portal_profile_pic_clear",
            run: function () {
                profilePictureSrc = document.querySelector(
                    ".o_portal_details .o_wportal_avatar_img"
                ).src;
                this.anchor.click();
            },
        },
        {
            content: "Check whether delete icon is removed or not",
            trigger: ".o_portal_details a:not(.o_portal_profile_pic_clear)",
        },
        {
            content: "Click on save button",
            trigger: ".o_portal_details button[type=submit]",
            run: "click",
        },
        {
            content: "Comparing previous Profile Picture with new One",
            trigger: ".o_portal_contact_img",
            run: function () {
                if (this.anchor.src == profilePictureSrc) {
                    throw new Error("Profile Picture is not removed after deletion!");
                }
            },
        },
    ],
});
