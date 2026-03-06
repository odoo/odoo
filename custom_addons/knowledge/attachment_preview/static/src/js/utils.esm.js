import {Component} from "@odoo/owl";

export function canPreview(extension) {
    const supported_extensions = [
        "odt",
        "odp",
        "ods",
        "fodt",
        "pdf",
        "ott",
        "fodp",
        "otp",
        "fods",
        "ots",
    ];
    return supported_extensions.includes(extension);
}

export function getUrl(
    attachment_id,
    attachment_url,
    attachment_extension,
    attachment_title
) {
    var url = "";
    if (attachment_url) {
        if (attachment_url.slice(0, 21) === "/web/static/lib/pdfjs") {
            // eslint-disable-next-line no-undef
            url = (window.location.origin || "") + attachment_url;
        } else {
            url =
                // eslint-disable-next-line no-undef
                (window.location.origin || "") +
                "/attachment_preview/static/lib/ViewerJS/index.html" +
                "?type=" +
                encodeURIComponent(attachment_extension) +
                "&title=" +
                encodeURIComponent(attachment_title) +
                "&zoom=automatic" +
                "#" +
                // eslint-disable-next-line no-undef
                attachment_url.replace(window.location.origin, "");
        }
        return url;
    }
    url =
        // eslint-disable-next-line no-undef
        (window.location.origin || "") +
        "/attachment_preview/static/lib/ViewerJS/index.html" +
        "?type=" +
        encodeURIComponent(attachment_extension) +
        "&title=" +
        encodeURIComponent(attachment_title) +
        "&zoom=automatic" +
        "#" +
        "/web/content/" +
        attachment_id +
        "?model%3Dir.attachment";

    return url;
}

export function showPreview(
    attachment_id,
    attachment_url,
    attachment_extension,
    attachment_title,
    split_screen,
    attachment_info_list
) {
    if (split_screen && attachment_info_list) {
        Component.env.bus.trigger("open_attachment_preview", {
            attachment_id,
            attachment_info_list,
        });
    } else {
        // eslint-disable-next-line no-undef
        window.open(
            getUrl(
                attachment_id,
                attachment_url,
                attachment_extension,
                attachment_title
            )
        );
    }
}
