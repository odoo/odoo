import { registry } from "@web/core/registry";
import {
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

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
            trigger: 'button[id=save_address]',
            run: "click",
        },
        {
            content: "Check that we are back on the portal",
            trigger: 'a[href*="/my/account"]:contains("Edit"):first',
        }
    ]
});

let previousProfilePictureSrc = "";

function compareProfilePictures(currentSrc) {
    if (currentSrc === previousProfilePictureSrc) {
        throw new Error("Profile Picture is not updated!");
    }
}

registerWebsitePreviewTour(
    "portal_profile_update",
    {
        url: "/my",
    },
    () => [
        {
            content: "Check portal is loaded",
            trigger: "a[href*='/my/account']",
            run: "click",
        },
        {
            content: "Update the profile picture using edit button",
            trigger: ".o_portal_picture_card",
            run: async function () {
                previousProfilePictureSrc = this.anchor.querySelector(".o_wportal_avatar_img").src;
                const fileInputEl = this.anchor.querySelector(".o_file_upload");
                const svgData =
                    "PHN2ZwogICAgICAgICAgICAgICAgICAgIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICAgICAgICAgICAgICAgICAgICB2aWV3Qm94PSIwIDAgNSA1Ij4KICAgICAgICAgICAgICAgICAgICA8Y2lyY2xlIGN4PSIyLjUiIGN5PSIyLjUiIHI9IjIiIGZpbGw9IiNmZGQ4MzUiLz4KICAgICAgICAgICAgICAgICAgICA8Y2lyY2xlIGN4PSIxLjciIGN5PSIyIiByPSIwLjMiIGZpbGw9IiMwMDAiLz4KICAgICAgICAgICAgICAgICAgICA8Y2lyY2xlIGN4PSIzLjMiIGN5PSIyIiByPSIwLjMiIGZpbGw9IiMwMDAiLz4KICAgICAgICAgICAgICAgICAgICA8cGF0aCBkPSJNMS41IDMuMiBRMi41IDQsIDMuNSAzLjIiIHN0cm9rZT0iIzAwMCIgc3Ryb2tlLXdpZHRoPSIwLjIiIGZpbGw9Im5vbmUiIC8+CiAgICAgICAgICAgICAgICA8L3N2Zz4=";
                const blob = new Blob([atob(svgData)], { type: "image/svg+xml" });
                const simulatedImageFile = new File([blob], "smiley.svg", {
                    type: blob.type,
                });
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(simulatedImageFile);
                fileInputEl.files = dataTransfer.files;

                fileInputEl.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
            },
        },
        {
            content: "Check if profile picture is updated successfully.",
            trigger: ".o_wportal_avatar_img",
            run: function () {
                compareProfilePictures(this.anchor.src);
            },
        },
        {
            content: "Click on save button",
            trigger: "button#save_address",
            run: "click",
        },
        {
            content: "Click on edit information",
            trigger: "a[href*='/my/account']:contains('Edit information')",
            run: "click",
        },
        {
            content: "Click on delete button",
            trigger: ".o_portal_profile_pic_clear",
            run: function () {
                previousProfilePictureSrc =
                    this.anchor.parentNode.parentNode.querySelector(".o_wportal_avatar_img").src;
                this.anchor.click();
            },
        },
        {
            content: "Click on save button",
            trigger: "button#save_address",
            run: "click",
        },
        {
            content: "Check if profile picture is updated successfully.",
            trigger: "img[alt=Contact]",
            run: function () {
                compareProfilePictures(this.anchor.src);
            },
        },
    ]
);
